"""Single *logical* access gateway, locally executable without opening a socket."""
from __future__ import annotations
from pathlib import Path
from .contracts import Action, InvalidRequest, receipt
from .policy import Policy, PolicyError
from .ledger import Ledger, LedgerError
from .adapters import Adapters, AdapterError

class Gateway:
    def __init__(self, config_file, state_dir):
        self.policy=Policy.load(config_file)
        self.state_dir=Path(state_dir)
        self.ledger=Ledger(self.state_dir/'master.sqlite3')
        self.adapters=Adapters(self.policy.cfg)
        self.stop_flag=self.state_dir/'STOP_ALL'

    def status(self):
        return {'version':'0.1.0-vNEXT-LAB', 'node_id':self.policy.node_id,
                'remote_listener':False, 'transport':'stdio',
                'stop':self.stop_flag.exists(), 'capabilities':self.policy.enabled()}

    def execute(self, raw):
        try:
            action=Action.parse(raw)
            decision=self.policy.decide(action)
            if self.stop_flag.exists() and action.capability!='host.status':
                raise PolicyError('GLOBAL_KILL_SWITCH_ACTIVE')
            phase, prev=self.ledger.claim(action,needs_approval=decision.approval)
            if phase=='EXISTING':
                return prev
            if phase=='NEEDS_APPROVAL':
                return receipt(action,'PENDING_LOCAL_APPROVAL', {'approve_digest':action.digest()},
                               'LOCAL_OWNER_APPROVAL_REQUIRED')
            try:
                result=self.adapters.execute(action.capability,action.params)
                rec=receipt(action,'COMPLETED',result)
            except (AdapterError, OSError, ValueError, TypeError):
                # Never leak local filesystem paths, headers or secret values in remote errors.
                rec=receipt(action,'FAILED',{},'ADAPTER_REJECTED_OR_UNAVAILABLE')
            self.ledger.finish(action,rec)
            return rec
        except (InvalidRequest,PolicyError,LedgerError) as err:
            return {'schema':'kai.master.receipt/1', 'status':'DENIED', 'error':str(err)}
