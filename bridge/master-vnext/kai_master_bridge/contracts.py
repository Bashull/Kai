"""Versioned, strictly typed KAI Master Bridge request/receipt contracts."""
from __future__ import annotations
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

SCHEMA = 'kai.master.action/1'
MAX_ARGS_BYTES = 32 * 1024

class InvalidRequest(ValueError):
    pass

def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, OverflowError) as ex:
        raise InvalidRequest('NON_JSON_INPUT') from ex

@dataclass(frozen=True)
class Action:
    request_id: str
    node_id: str
    capability: str
    params: dict
    deadline: int

    @classmethod
    def parse(cls, data: Any, now: int | None = None):
        if not isinstance(data, dict) or set(data) != {'schema', 'request_id', 'node_id', 'capability', 'params', 'deadline'}:
            raise InvalidRequest('INVALID_SCHEMA')
        if data['schema'] != SCHEMA:
            raise InvalidRequest('UNKNOWN_PROTOCOL')
        try:
            rid = str(uuid.UUID(data['request_id']))
            if rid != data['request_id'] or uuid.UUID(rid).version != 4:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise InvalidRequest('INVALID_REQUEST_ID') from None
        node, cap, args = data['node_id'], data['capability'], data['params']
        if not isinstance(node, str) or not (1 <= len(node) <= 64) or not all(c.isalnum() or c in '._-' for c in node):
            raise InvalidRequest('INVALID_NODE_ID')
        if not isinstance(cap, str) or not (1 <= len(cap) <= 96) or not all(c.isalnum() or c in '._-' for c in cap):
            raise InvalidRequest('INVALID_CAPABILITY')
        if not isinstance(args, dict) or len(canonical(args)) > MAX_ARGS_BYTES:
            raise InvalidRequest('INVALID_PARAMS')
        deadline = data['deadline']
        current = int(time.time()) if now is None else int(now)
        if type(deadline) is not int or deadline < current or deadline > current + 300:
            raise InvalidRequest('STALE_OR_FUTURE_DEADLINE')
        return cls(rid, node, cap, args, deadline)

    def digest(self) -> str:
        return hashlib.sha256(canonical({'schema': SCHEMA, 'request_id': self.request_id,
            'node_id': self.node_id, 'capability': self.capability,
            'params': self.params, 'deadline': self.deadline})).hexdigest()


def receipt(action: Action, status: str, result: dict | None = None, error: str | None = None) -> dict:
    return {'schema': 'kai.master.receipt/1', 'request_id': action.request_id,
            'node_id': action.node_id, 'capability': action.capability,
            'digest': action.digest(), 'status': status,
            'result': result if result is not None else {}, 'error': error}
