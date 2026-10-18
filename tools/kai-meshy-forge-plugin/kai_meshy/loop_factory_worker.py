"""Read-only Forge worker for the existing guarded KAI Loop Factory runner.

The runtime owner supplies its real fence type, StepOutcome contract and
LoopStore. This worker emits a projection artifact, never a LoopFactory or
vendor receipt. Paid APIs and the unguarded Worker.run path are unavailable.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from .core import ForgeError, _no_symlink, digest
from .loop_factory_adapter import JOB_ID, observation_projection


class ForgeObservationWorker:
    worker_id = 'kai_meshy_get_job'
    estimated_cost_eur = 0.0

    def __init__(self, forge, forge_job_id, sandbox, *, loop_store, outcome_type, fence_type):
        if not isinstance(forge_job_id,str) or not JOB_ID.fullmatch(forge_job_id):
            raise ForgeError('OBSERVATION_JOB_ID_INVALID')
        self.forge=forge
        self.forge_job_id=forge_job_id
        self.sandbox=_no_symlink(sandbox).resolve()
        self.loop_store=loop_store
        self.outcome_type=outcome_type
        self.fence_type=fence_type
        self.run_calls=0

    def output_path(self):
        return self.sandbox/'forge-observation.json'

    def assert_dependencies(self, job):
        """Read dependency state from the supplied existing LoopStore.

        The control-plane caller should invoke this before dispatch; the worker
        repeats it inside its guarded call to close a stale preflight window.
        This function neither claims nor updates a dependency.
        """
        if not isinstance(job.dependencies,list):
            raise ForgeError('OBSERVATION_DEPENDENCY_LIST_INVALID')
        for dependency_id in job.dependencies:
            if dependency_id==job.job_id:
                raise ForgeError('OBSERVATION_SELF_DEPENDENCY_DENIED')
            try:
                dependency=self.loop_store.get_job(dependency_id)
            except KeyError:
                raise ForgeError('OBSERVATION_DEPENDENCY_NOT_FOUND') from None
            if getattr(dependency.state,'value',dependency.state)!='SUCCEEDED':
                raise ForgeError('OBSERVATION_DEPENDENCY_NOT_SUCCEEDED')

    def run(self, context):
        raise ForgeError('OBSERVATION_REQUIRES_EXISTING_GUARDED_RUNNER')

    def _context_scope(self, context):
        if Path(context.sandbox).resolve()!=self.sandbox:
            raise ForgeError('OBSERVATION_SANDBOX_MISMATCH')
        if context.job.allowed_tools!=[self.worker_id] or context.job.input_refs!=['kai-meshy:job:'+self.forge_job_id]:
            raise ForgeError('OBSERVATION_READ_SCOPE_MISMATCH')
        if getattr(context.job.autonomy_level,'value',context.job.autonomy_level)!='A0':
            raise ForgeError('OBSERVATION_REQUIRES_A0')
        if context.job.budget.max_cost_eur!=0 or context.job.budget.max_retries!=0:
            raise ForgeError('OBSERVATION_SCOPE_MUST_REMAIN_ZERO_COST_NO_RETRY')

    def run_guarded(self, context, fence):
        self._context_scope(context)
        if not isinstance(fence,self.fence_type):
            raise ForgeError('OBSERVATION_EXISTING_FENCE_TYPE_REQUIRED')
        fence.require(context.job.job_id,self.worker_id,self.sandbox)
        self.assert_dependencies(context.job)
        projection=observation_projection(self.forge.get_job(self.forge_job_id))
        projection_sha=hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if (context.job.input_hashes.get('forge_observation_sha256')!=projection_sha or
                context.job.input_hashes.get('forge_source_sha256')!=projection['source_sha256']):
            raise ForgeError('OBSERVATION_INPUT_CHANGED_REPLAN_WITHOUT_VENDOR_SUBMISSION')
        body={'schema':'kai.meshy.observation-artifact/1','scope':'READ_ONLY_DOMAIN_OBSERVATION_NOT_A_RECEIPT',
              'loop_input_hash':context.input_hash,'projection':projection}
        raw=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
        if len(raw)>32768:
            raise ForgeError('OBSERVATION_ARTIFACT_TOO_LARGE')
        self.sandbox.mkdir(parents=True,exist_ok=True,mode=0o700)
        target=_no_symlink(self.output_path())
        fd,name=tempfile.mkstemp(prefix='observation-',suffix='.part',dir=self.sandbox)
        part=Path(name)
        try:
            with os.fdopen(fd,'wb') as out:
                out.write(raw);out.flush();os.fsync(out.fileno())
            self.assert_dependencies(context.job)
            fence.require(context.job.job_id,self.worker_id,self.sandbox)
            try:
                final_fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            except FileExistsError:
                if digest(_no_symlink(target))!=hashlib.sha256(raw).hexdigest():
                    raise ForgeError('OBSERVATION_IMMUTABLE_OUTPUT_CONFLICT') from None
            else:
                # Android Python has no os.link. Exclusive creation never
                # overwrites an original. A failed partial stays diagnostic;
                # the existing runner's UNKNOWN journal prohibits replay.
                with os.fdopen(final_fd,'wb') as out:
                    out.write(raw);out.flush();os.fsync(out.fileno())
            self.run_calls+=1
            return self.outcome_type(output_hash=hashlib.sha256(raw).hexdigest(),
                                     evidence_summary='Verified read-only Forge projection; no vendor request',
                                     cost_eur=0.0,verified=True)
        finally:
            part.unlink(missing_ok=True)

    def verify(self, context, output_hash):
        """Verify the historical projection artifact; never rerun its producer."""
        try:
            self._context_scope(context)
            target=_no_symlink(self.output_path())
            if not target.is_file() or target.stat().st_size>32768 or digest(target)!=output_hash:
                return False
            body=json.loads(target.read_text())
            if (set(body)!={'schema','scope','loop_input_hash','projection'} or
                    body['schema']!='kai.meshy.observation-artifact/1' or
                    body['scope']!='READ_ONLY_DOMAIN_OBSERVATION_NOT_A_RECEIPT' or
                    body['loop_input_hash']!=context.input_hash):
                return False
            projection=body['projection']
            raw=json.dumps(projection,sort_keys=True,separators=(',',':')).encode()
            return (projection.get('forge_job_id')==self.forge_job_id and
                    hashlib.sha256(raw).hexdigest()==context.job.input_hashes['forge_observation_sha256'] and
                    projection.get('source_sha256')==context.job.input_hashes['forge_source_sha256'])
        except (ForgeError,OSError,ValueError,TypeError,KeyError,AttributeError):
            return False
