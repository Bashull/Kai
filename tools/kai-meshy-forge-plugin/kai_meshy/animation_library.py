"""Fixed, free Animation Library read and short-lived action membership proof.

The official animation documentation states that library GET is free, returns
the complete list, and shares its accepted IDs with animation creation. IDs are
not contiguous; a numeric range is insufficient. Documentation snapshot SHA256:
e79a4f3aa993de448835a0998448b2400e4e3accbe8851df2ba5af05db47f663.

This original KAI adapter retains five public metadata fields only. It does not
persist a cache, fetch GIFs, open the CLI authentication store, grant spending
permission, or expose a caller-selected endpoint. A five-minute local freshness
limit is a conservative policy, not a guarantee against vendor retirement.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re

from .core import ForgeError


FRESHNESS_SECONDS = 300
MAX_ENTRIES = 5000
MAX_SAFE_BYTES = 2 * 1024 * 1024
DOC_SNAPSHOT_SHA256 = 'e79a4f3aa993de448835a0998448b2400e4e3accbe8851df2ba5af05db47f663'
_FIELDS = ('action_id', 'name', 'key', 'category', 'sub_category')
_UNSAFE_TEXT = re.compile(r'https?://|data:|msy_|Bearer\s|[?&](?:Expires|Signature)=', re.I)


class AnimationLibraryError(ForgeError):
    """Safe error codes never include provider replies or caller values."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _utc_now():
    return datetime.now(timezone.utc)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _fixed_contract():
    # A new private dictionary on every invocation prevents caller mutation of
    # module-level routing state. There are no parameters or alternate methods.
    return {'id': 'animation.library.read', 'api_version': 'v1', 'auth_family': 'v1',
            'routes': {'get': '/openapi/v1/animations/library'},
            'route_methods': {'get': 'GET'}}


def _response_rows(response):
    if not isinstance(response, dict) or response.get('ok') is False:
        raise AnimationLibraryError('ANIMATION_LIBRARY_RESPONSE_INVALID')
    if 'result' in response:
        if response.get('ok') is not True:
            raise AnimationLibraryError('ANIMATION_LIBRARY_RESPONSE_INVALID')
        if response.get('schema_version', 'meshy.cli/v1') != 'meshy.cli/v1' or response.get('command', 'api') != 'api':
            raise AnimationLibraryError('ANIMATION_LIBRARY_RESPONSE_INVALID')
        transport = response['result']
    else:
        # Some internal CLI adapters already remove the outer CLI envelope.
        # They must still retain exact transport metadata; a raw array is not
        # accepted as proof of which method/resource was actually requested.
        transport = response
    if not isinstance(transport, dict):
        raise AnimationLibraryError('ANIMATION_LIBRARY_TRANSPORT_INVALID')
    if (type(transport.get('http_status')) is not int or transport['http_status'] != 200 or
            transport.get('method') != 'GET' or transport.get('api') != 'v1' or
            transport.get('path') not in {'/animations/library', '/openapi/v1/animations/library'}):
        raise AnimationLibraryError('ANIMATION_LIBRARY_TRANSPORT_INVALID')
    rows = transport.get('body')
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ENTRIES:
        raise AnimationLibraryError('ANIMATION_LIBRARY_LIST_INVALID')
    return rows


def _safe_rows(rows):
    safe, seen_ids, seen_keys = [], set(), set()
    for item in rows:
        if not isinstance(item, dict) or type(item.get('action_id')) is not int or item['action_id'] < 0:
            raise AnimationLibraryError('ANIMATION_LIBRARY_ACTION_ID_INVALID')
        row = {'action_id': item['action_id']}
        for field in _FIELDS[1:]:
            value = item.get(field)
            if (not isinstance(value, str) or not 1 <= len(value) <= 512 or
                    any(not char.isprintable() for char in value) or _UNSAFE_TEXT.search(value)):
                raise AnimationLibraryError('ANIMATION_LIBRARY_METADATA_INVALID')
            row[field] = value
        if row['action_id'] in seen_ids or row['key'] in seen_keys:
            raise AnimationLibraryError('ANIMATION_LIBRARY_IDENTITY_DUPLICATE')
        seen_ids.add(row['action_id']); seen_keys.add(row['key'])
        safe.append(row)
    # The provider promises ordering, but normalization makes equivalent safe
    # content have the same fingerprint even if its transport order changes.
    safe.sort(key=lambda row: row['action_id'])
    encoded = _canonical(safe)
    if len(encoded) > MAX_SAFE_BYTES:
        raise AnimationLibraryError('ANIMATION_LIBRARY_METADATA_TOO_LARGE')
    return safe, hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, init=False)
class AnimationLibrary:
    """Immutable, in-memory snapshot obtained only through a fixed CLI GET."""

    _rows: tuple
    _fingerprint: str
    _fetched_at: datetime

    @classmethod
    def fetch(cls, cli, timeout=30):
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or
                not math.isfinite(timeout) or not 0 < timeout <= 60):
            raise AnimationLibraryError('ANIMATION_LIBRARY_TIMEOUT_INVALID')
        try:
            response = cli.request(_fixed_contract(), 'get', timeout=timeout)
        except Exception:
            # An injected CLI implementation might include credentials in its
            # exception. Its message and repr must never enter public output.
            raise AnimationLibraryError('ANIMATION_LIBRARY_FETCH_FAILED') from None
        rows, fingerprint = _safe_rows(_response_rows(response))
        snapshot = object.__new__(cls)
        object.__setattr__(snapshot, '_rows', tuple(tuple(row[field] for field in _FIELDS) for row in rows))
        object.__setattr__(snapshot, '_fingerprint', fingerprint)
        object.__setattr__(snapshot, '_fetched_at', _utc_now())
        return snapshot

    @property
    def fingerprint_sha256(self):
        return self._fingerprint

    @property
    def fetched_at_utc(self):
        return self._fetched_at.isoformat()

    @property
    def expires_at_utc(self):
        return (self._fetched_at + timedelta(seconds=FRESHNESS_SECONDS)).isoformat()

    @property
    def action_count(self):
        return len(self._rows)

    @property
    def allowed_ids(self):
        return frozenset(row[0] for row in self._rows)

    @property
    def entries(self):
        return [dict(zip(_FIELDS, row)) for row in self._rows]

    @property
    def source(self):
        return {'method': 'GET', 'endpoint': '/openapi/v1/animations/library',
                'api_version': 'v1', 'auth_family': 'v1', 'http_status': 200,
                'documentation_snapshot_sha256': DOC_SNAPSHOT_SHA256,
                'documentation_free_statement_lines': '702-708',
                'documentation_membership_and_retirement_line': 751,
                'canonicalization': 'UTF8_JSON_SORTED_KEYS_COMPACT_ROWS_SORTED_ACTION_ID',
                'retained_fields': list(_FIELDS), 'preview_resources_retained': False,
                'freshness_seconds': FRESHNESS_SECONDS,
                'retirement_possible_before_expiry': True,
                'credits': 0, 'authorization': 'NOT_GRANTED_BY_LIBRARY'}

    def _require_fresh(self):
        age = (_utc_now() - self._fetched_at).total_seconds()
        if age < 0 or age >= FRESHNESS_SECONDS:
            raise AnimationLibraryError('ANIMATION_LIBRARY_STALE_OR_FUTURE')

    def require_action(self, action_id):
        if type(action_id) is not int or action_id < 0:
            raise AnimationLibraryError('ANIMATION_ACTION_ID_INVALID')
        self._require_fresh()
        for row in self._rows:
            if row[0] == action_id:
                return {**dict(zip(_FIELDS, row)), 'library_fingerprint': self._fingerprint,
                        'verified_utc': self.fetched_at_utc}
        raise AnimationLibraryError('ANIMATION_ACTION_NOT_IN_CURRENT_LIBRARY')

    def require_actions(self, action_ids):
        if not isinstance(action_ids, (list, tuple)) or not 1 <= len(action_ids) <= 10:
            raise AnimationLibraryError('ANIMATION_ACTION_IDS_INVALID')
        # Validate types before hashing; None, bool, unhashable containers and
        # float representations must not acquire integer identity implicitly.
        if any(type(value) is not int or value < 0 for value in action_ids):
            raise AnimationLibraryError('ANIMATION_ACTION_ID_INVALID')
        if len(set(action_ids)) != len(action_ids):
            raise AnimationLibraryError('ANIMATION_ACTION_IDS_DUPLICATE')
        return [self.require_action(value) for value in action_ids]

    def to_receipt(self, action_ids=None):
        self._require_fresh()
        receipt = {'fingerprint_sha256': self._fingerprint, 'fetched_at_utc': self.fetched_at_utc,
                   'expires_at_utc': self.expires_at_utc, 'action_count': self.action_count,
                   'source': self.source, 'authorization': 'NOT_GRANTED_BY_LIBRARY'}
        if action_ids is not None:
            receipt['action_ids'] = [row['action_id'] for row in self.require_actions(action_ids)]
        return receipt

    def as_dict(self):
        return {**self.to_receipt(), 'items': self.entries}

    def query(self, *, category=None, search=None, offset=0, limit=25):
        """Filter this snapshot locally, without another vendor request."""
        self._require_fresh()
        if (type(offset) is not int or offset < 0 or
                type(limit) is not int or not 1 <= limit <= 100):
            raise AnimationLibraryError('ANIMATION_LIBRARY_PAGE_INVALID')
        categories = {row[3] for row in self._rows}
        if category is not None and (not isinstance(category, str) or category not in categories):
            raise AnimationLibraryError('ANIMATION_LIBRARY_CATEGORY_INVALID')
        if search is not None and (not isinstance(search, str) or len(search) > 128 or
                                   any(not c.isprintable() for c in search) or _UNSAFE_TEXT.search(search)):
            raise AnimationLibraryError('ANIMATION_LIBRARY_SEARCH_INVALID')
        needle = search.casefold() if search is not None else ''
        matching = [row for row in self._rows if (category is None or row[3] == category) and
                    (not needle or needle in row[1].casefold() or needle in row[2].casefold())]
        page = matching[offset:offset + limit]
        next_offset = offset + len(page)
        return {**self.to_receipt(), 'provider_count': self.action_count,
                'matched_count': len(matching), 'offset': offset, 'limit': limit,
                'next_offset': next_offset if next_offset < len(matching) else None,
                'items': [dict(zip(_FIELDS, row)) for row in page]}
