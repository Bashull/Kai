"""Explicit source-of-authority policy; transport possession never grants execution."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

READ_CAPS = {'host.status', 'fs.list', 'fs.sha256', 'pc.agent.health', 'pc.agent.apps',
             'android.adb.devices', 'android.adb.model'}
ACT_CAPS = {'pc.agent.launch', 'android.adb.launch'}
HIGH_TRUST = {'pc.gui.windows'}
KNOWN = READ_CAPS | ACT_CAPS | HIGH_TRUST

class PolicyError(PermissionError):
    pass

@dataclass(frozen=True)
class Decision:
    effect: str
    approval: bool

class Policy:
    def __init__(self, settings: dict):
        self.cfg = settings
        self.node_id = settings.get('node_id')
        if not isinstance(self.node_id, str) or not self.node_id:
            raise PolicyError('NODE_NOT_CONFIGURED')
        caps = settings.get('capabilities', {})
        if not isinstance(caps, dict) or set(caps) - KNOWN:
            raise PolicyError('UNKNOWN_POLICY_CAPABILITY')
        self.caps = caps

    @classmethod
    def load(cls, path: str | Path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def decide(self, action):
        if action.node_id != self.node_id:
            raise PolicyError('UNKNOWN_NODE')
        setting = self.caps.get(action.capability, {})
        if not isinstance(setting, dict) or not setting.get('enabled', False):
            raise PolicyError('CAPABILITY_DISABLED')
        if action.capability not in KNOWN:
            raise PolicyError('UNKNOWN_CAPABILITY')
        return Decision('ACT' if action.capability in ACT_CAPS else 'OBSERVE',
                        action.capability in (ACT_CAPS | HIGH_TRUST))

    def enabled(self):
        return sorted(k for k, v in self.caps.items() if v.get('enabled'))
