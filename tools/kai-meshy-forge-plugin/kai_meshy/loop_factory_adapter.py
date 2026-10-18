"""Pure observation envelopes for the existing KAI Loop Factory contract.

This module does not instantiate LoopStore/LoopRunner, register a worker, write
receipts or submit vendor tasks. The caller injects the existing model module.
Meshy credit reservations stay in Forge; CELL-000's EUR budget stays zero.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping, Protocol, Sequence

from .core import ForgeError

MODEL_SHA256 = 'f882fd7446387022dd1ecd7d5ef60a93e8e634585e84016ff22cdbf26fe13540'
JOB_ID = re.compile(r'^[a-zA-Z0-9_-]{1,70}$')
SHA256 = re.compile(r'^[a-f0-9]{64}$')
TASK_ID = re.compile(r'^[a-zA-Z0-9-]{8,100}$')
AUTHORITY_REF = re.compile(r'^(?:drive:[a-zA-Z0-9_-]+|git:[a-f0-9]{7,40}|doc:[a-zA-Z0-9_.-]+)$')
DOMAIN_STATUSES = {'SUBMISSION_UNKNOWN','PENDING','IN_PROGRESS','SUCCEEDED','FAILED','CANCELED'}


class LoopManifest(Protocol):
    def to_dict(self) -> dict[str, object]: ...
    def to_json(self) -> str: ...


class LoopFactoryModel(Protocol):
    JobManifest: Any
    Budget: Any
    AutonomyLevel: Any


def _flag(value):
    if isinstance(value, bool) or (type(value) is int and value in (0,1)):
        return bool(value)
    raise ForgeError('LOOP_PROJECTION_FLAG_INVALID')


def _credit(value, *, optional=False):
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
        raise ForgeError('LOOP_PROJECTION_CREDIT_INVALID')
    return value


def observation_projection(snapshot: Mapping[str, Any]) -> dict[str, object]:
    """Whitelist a read-only domain observation; paths, payloads and URLs vanish."""
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get('job'), Mapping):
        raise ForgeError('LOOP_FORGE_SNAPSHOT_INVALID')
    job = snapshot['job']
    job_id = job.get('id'); source_sha = job.get('source_sha'); budget = job.get('budget')
    if not isinstance(job_id,str) or not JOB_ID.fullmatch(job_id):
        raise ForgeError('LOOP_FORGE_JOB_ID_INVALID')
    if not isinstance(source_sha,str) or not SHA256.fullmatch(source_sha):
        raise ForgeError('LOOP_FORGE_SOURCE_HASH_INVALID')
    if type(budget) is not int or not 1 <= budget <= 500:
        raise ForgeError('LOOP_FORGE_BUDGET_INVALID')
    stages = snapshot.get('stages', [])
    if not isinstance(stages,list) or len(stages)>2:
        raise ForgeError('LOOP_FORGE_STAGES_INVALID')
    result_stages=[]; seen=set()
    for stage in stages:
        if not isinstance(stage, Mapping):
            raise ForgeError('LOOP_FORGE_STAGE_INVALID')
        name=stage.get('stage'); status=stage.get('status'); task_id=stage.get('task_id')
        if name not in {'prototype','build'} or name in seen or status not in DOMAIN_STATUSES:
            raise ForgeError('LOOP_FORGE_STAGE_INVALID')
        if task_id is not None and (not isinstance(task_id,str) or not TASK_ID.fullmatch(task_id)):
            raise ForgeError('LOOP_FORGE_TASK_ID_INVALID')
        seen.add(name)
        result_stages.append({'stage':name,'status':status,'task_id':task_id,
                              'reserved_meshy_credits':_credit(stage.get('reservation',0)),
                              'actual_meshy_credits':_credit(stage.get('actual'),optional=True)})
    return {'schema':'kai.meshy.loop-observation/1','forge_job_id':job_id,'source_sha256':source_sha,
            'meshy_job_budget_credits':budget,
            'preview_approved':_flag(job.get('preview_approved',0)),
            'local_cancelled':_flag(job.get('local_cancelled',0)),
            'rejected':_flag(job.get('rejected',0)),
            'stages':sorted(result_stages,key=lambda stage:stage['stage']),
            'scope':'READ_ONLY_OBSERVATION; NOT_A_VENDOR_OR_LOOP_FACTORY_RECEIPT'}


def make_observation_manifest(snapshot: Mapping[str, Any], *, lf_model: LoopFactoryModel,
                              authority_refs: Sequence[str]=(), dependencies: Sequence[str]=()) -> LoopManifest:
    """Construct the actual injected JobManifest; never create/store/run a job.

    Empty write_scope intentionally prevents the baseline runner from executing
    until its owner provides a governed observation worker/scope. No autonomy,
    Meshy budget or approval is inherited from a domain task's success flag.
    """
    projection=observation_projection(snapshot)
    if isinstance(authority_refs,(str,bytes)) or not all(isinstance(x,str) and AUTHORITY_REF.fullmatch(x) for x in authority_refs):
        raise ForgeError('LOOP_AUTHORITY_REFS_MUST_BE_EXPLICIT_IDS')
    if isinstance(dependencies,(str,bytes)) or not all(isinstance(x,str) and re.fullmatch(r'[a-zA-Z0-9_.:-]{1,150}',x) for x in dependencies):
        raise ForgeError('LOOP_DEPENDENCY_IDS_INVALID')
    raw=json.dumps(projection,sort_keys=True,separators=(',',':')).encode()
    state_sha=hashlib.sha256(raw).hexdigest()
    try:
        manifest=lf_model.JobManifest.new(
            job_id='MESHY_OBSERVE_'+projection['forge_job_id']+'_'+state_sha[:16],
            project='KAI_MEDIA_FORGE_OMEGA',cell_type='MESHY_READ_ONLY_OBSERVATION',
            goal='Observe the existing Forge job through its typed read-only tool; preserve domain authority.',
            current_authority_refs=list(authority_refs),input_refs=['kai-meshy:job:'+projection['forge_job_id']],
            input_hashes={'forge_source_sha256':projection['source_sha256'],'forge_observation_sha256':state_sha},
            dependencies=list(dependencies),allowed_tools=['kai_meshy_get_job'],write_scope=[],
            autonomy_level=lf_model.AutonomyLevel.A0,
            budget=lf_model.Budget(currency='EUR',max_cost_eur=0.0,max_iterations=1,max_retries=0,timeout_seconds=30),
        )
        return lf_model.JobManifest.from_json(manifest.to_json())
    except (AttributeError,TypeError,ValueError):
        raise ForgeError('LOOP_FACTORY_CONTRACT_INCOMPATIBLE') from None
