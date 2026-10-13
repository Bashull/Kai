"""Fail-closed federation for the existing Windows/Termux KAI transports.

Enforces validated intents, bounded freshness and local-consent gates.
It builds *requests* and route plans, and NEVER sends a click or executes shell.
This is not an access token or a cryptographic signature.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import re
import uuid
from typing import Any, Mapping

class RouteError(ValueError):
    pass

@dataclass(frozen=True)
class Capability:
    name: str
    node: str
    backend: str
    trust: str
    status: str
    required_proofs: tuple[str, ...] = ()

# Only empirically established, scoped capabilities are routable.
# A donor's source code or a historic test is never automatically a live endpoint.
REGISTRY: dict[str, Capability] = {
    'windows.status': Capability('host.status','kai-pc-asier','sentinel-kai-inbox','READ','VERIFIED_SCOPE'),
    'windows.gui.count': Capability('pc.gui.observe','kai-pc-asier','sentinel-kai-inbox','READ','VERIFIED_SCOPE'),
    'windows.apps.catalog': Capability('pc.agent.apps','kai-pc-asier','sentinel-kai-inbox','READ','VERIFIED_SCOPE'),
    'windows.agent.health': Capability('pc.agent.health','kai-pc-asier','sentinel-kai-inbox','READ','VERIFIED_SCOPE'),
    'android.status': Capability('status','kai-galaxy-s24','termux-kai-phone','READ','VERIFIED_SCOPE'),
    'android.apps.kai': Capability('apps kai','kai-galaxy-s24','termux-kai-phone','READ','VERIFIED_SCOPE'),
    'android.gui.tap': Capability('tap','kai-galaxy-s24','termux-kai-phone','ACT','LOCAL_ONLY',('foreground_package','local_owner_approval')),
    'windows.gui.catalog': Capability('pc.gui.catalog','kai-pc-asier','sentinel-kai-inbox','READ','STAGING'),
    'windows.gui.capture': Capability('pc.gui.capture','kai-pc-asier','sentinel-kai-inbox','SENSITIVE','STAGING',('local_owner_approval','foreground_window_fingerprint','unlocked_session')),
    'windows.gui.click': Capability('pc.gui.click','kai-pc-asier','sentinel-kai-inbox','ACT','STAGING',('local_owner_approval','foreground_window_fingerprint','unlocked_session')),
    'windows.gui.type': Capability('pc.gui.type','kai-pc-asier','sentinel-kai-inbox','ACT','STAGING',('local_owner_approval','foreground_window_fingerprint','unlocked_session')),
    'android.root': Capability('root','kai-galaxy-s24','none','ADMIN','UNAVAILABLE'),
    'windows.admin.shell': Capability('powershell.run','kai-pc-asier','none','ADMIN','UNAVAILABLE'),
}

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$')

@dataclass(frozen=True)
class Evidence:
    node: str
    capability: str
    observed_at: int
    transport: str
    result: str
    origin: str = 'tool_observation'

@dataclass(frozen=True)
class Intent:
    capability: str
    request_id: str
    issued_at: int
    expires_at: int
    params: Mapping[str, Any]

@dataclass(frozen=True)
class RoutePlan:
    logical_capability: str
    node: str
    backend: str
    mode: str
    required_proofs: tuple[str, ...]
    expiry: int


def _is_valid_uuid(value: str) -> bool:
    return isinstance(value, str) and UUID_PATTERN.fullmatch(value) is not None

def classify(capability: str) -> str:
    """Does not imply real-time availability; classified source/provenance only."""
    item = REGISTRY.get(capability)
    if item is None:
        return 'UNKNOWN'
    return item.status


def validate_intent(intent: Intent, *, now: int) -> Capability:
    if type(now) is not int or now < 0:
        raise RouteError('CLOCK_INVALID')
    if not isinstance(intent, Intent) or intent.capability not in REGISTRY:
        raise RouteError('CAPABILITY_UNKNOWN')
    if not _is_valid_uuid(intent.request_id):
        raise RouteError('REQUEST_ID_INVALID')
    if type(intent.issued_at) is not int or type(intent.expires_at) is not int:
        raise RouteError('TTL_INVALID')
    if intent.issued_at > now or intent.expires_at <= now:
        raise RouteError('REQUEST_NOT_CURRENT')
    if intent.expires_at - intent.issued_at > 120 or intent.expires_at <= intent.issued_at:
        raise RouteError('TTL_EXCEEDS_BOUND')
    if type(intent.params) is not dict:
        raise RouteError('PARAMS_REJECTED')
    try:
        args = json.dumps(intent.params, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError) as exc:
        raise RouteError('PARAMS_NOT_CANONICAL') from exc
    if len(args) > 4096:
        raise RouteError('PARAMS_TOO_LARGE')
    item=REGISTRY[intent.capability]
    if item.trust == 'READ' and intent.params:
        raise RouteError('READ_PARAMS_NOT_SUPPORTED')
    return item


def plan_route(intent: Intent, evidence: Evidence | None, *, now: int,
               proofs: Mapping[str, Any] | None = None) -> RoutePlan:
    item = validate_intent(intent, now=now)
    # For now all ACT, ADMIN, SENSITIVE or STAGING operations are nonroutable.
    # Declared local approval DOES NOT grant remote unattended execution.
    if item.status != 'VERIFIED_SCOPE' or item.trust != 'READ':
        raise RouteError('CAPABILITY_NOT_ENABLED_FOR_REMOTE_EXECUTION')
    if not isinstance(evidence, Evidence) or evidence.node != item.node or evidence.capability != intent.capability:
        raise RouteError('MATCHING_EVIDENCE_REQUIRED')
    if evidence.transport != item.backend or evidence.result != 'COMPLETED' or evidence.origin != 'tool_observation':
        raise RouteError('EVIDENCE_NOT_TRUSTED')
    if type(evidence.observed_at) is not int or not 0 <= now-evidence.observed_at <= 120:
        raise RouteError('EVIDENCE_STALE')
    if proofs and set(proofs):
        raise RouteError('UNEXPECTED_PROOFS_FOR_READ')
    return RoutePlan(intent.capability,item.node,item.backend,'READ_ONLY',(),intent.expires_at)


def make_action(intent: Intent, evidence: Evidence, *, now: int) -> dict:
    """Construct a KAI-compatible Windows Action; does not transmit it."""
    plan = plan_route(intent,evidence,now=now)
    if plan.backend != 'sentinel-kai-inbox':
        raise RouteError('NOT_A_WINDOWS_QUEUE_ACTION')
    item=REGISTRY[intent.capability]
    return {'schema':'kai.master.action/1','request_id':intent.request_id,
            'node_id':item.node,'capability':item.name,
            'params':dict(intent.params),'deadline':intent.expires_at}


def digest_action(action: Mapping[str, Any]) -> str:
    """SHA-256 content binder only. No claim of HMAC or digital signature."""
    return hashlib.sha256(json.dumps(action,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def verify_receipt(action: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict:
    expected={'schema','request_id','node_id','capability','digest','status','result','error'}
    if type(receipt) is not dict or set(receipt)!=expected:
        raise RouteError('RECEIPT_SCHEMA_INVALID')
    if receipt['schema']!='kai.master.receipt/1':
        raise RouteError('RECEIPT_VERSION_INVALID')
    for k in ('request_id','node_id','capability'):
        if receipt[k]!=action.get(k):
            raise RouteError('RECEIPT_IDENTITY_MISMATCH')
    if not isinstance(receipt['digest'],str) or not SHA256_PATTERN.fullmatch(receipt['digest']):
        raise RouteError('DIGEST_BAD_FORMAT')
    if receipt['digest']!=digest_action(action):
        raise RouteError('RECEIPT_DIGEST_MISMATCH')
    if receipt['status'] not in ('COMPLETED','FAILED','DENIED','PENDING_LOCAL_APPROVAL'):
        raise RouteError('RECEIPT_STATUS_UNKNOWN')
    if type(receipt['result']) is not dict:
        raise RouteError('RESULT_INVALID')
    if receipt['status']=='COMPLETED' and receipt['error'] is not None:
        raise RouteError('COMPLETED_WITH_ERROR')
    return dict(receipt)


def route_summary() -> dict[str, Any]:
    return {'schema':'kai.unified.catalog/1',
            'control_plane':'candidate-not-deployed',
            'node_count':len({x.node for x in REGISTRY.values()}),
            'routable_read_paths':[k for k,x in REGISTRY.items() if x.trust=='READ' and x.status=='VERIFIED_SCOPE'],
            'high_trust_routable':False,
            'candidate_adds_listening_port':False,
            'live_integrations':False}