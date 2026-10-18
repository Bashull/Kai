"""Actual guarded LF runner/store with disposable copied LAB authorities only.

No production identity, historical DB, vendor call, Gateway, or service is used.
Synthetic signed leases retain their original LAB-only meaning.
"""
from contextlib import closing
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import shutil
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from uuid import uuid4

from PIL import Image
from kai_meshy.core import Forge, ForgeError
from kai_meshy.capability_engine import CapabilityEngine
from kai_meshy.loop_factory_adapter import make_observation_manifest
from kai_meshy.loop_factory_worker import ForgeObservationWorker

SOURCE=Path.home()/'KAI_ONE_MIND_LAB/F02_F01_RECONCILIATION_20261015/CELL_F02_014C_WORK_20261016/runtime/candidate_013R_audit_fix_20261015'
SCENARIOS=[]
CASE_SCHEMA=('CREATE TABLE case_control(case_id TEXT PRIMARY KEY,mode TEXT NOT NULL CHECK(mode IN '
             "('RUNNING','PAUSED','CANCELLED')),epoch INTEGER NOT NULL DEFAULT 0,reason_code TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL)")


class NoVendor:
    def __init__(self):self.calls=0
    def api(self,*args,**kwargs):self.calls+=1;raise AssertionError('VENDOR_CALL_FORBIDDEN')
    auth=balance=request=api


class CountingForge:
    def __init__(self,forge):self.forge=forge;self.reads=0
    def get_job(self,job_id):self.reads+=1;return self.forge.get_job(job_id)


@unittest.skipUnless((SOURCE/'bridge_auth_012.py').is_file(),'Existing guarded LF source unavailable; no synthetic replacement')
class ExistingGuardedRunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent=tempfile.TemporaryDirectory(prefix='kai-lf-source-copy-')
        cls.copy=Path(cls.parent.name)/'candidate_013R'
        cls.hashes={}
        for source in SOURCE.rglob('*.py'):
            relative=source.relative_to(SOURCE)
            if any(part in {'fixtures','__pycache__','tests'} for part in relative.parts):continue
            dest=cls.copy/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,dest)
            sha=hashlib.sha256(source.read_bytes()).hexdigest()
            assert hashlib.sha256(dest.read_bytes()).hexdigest()==sha
            cls.hashes[str(relative)]=sha
        (cls.copy/'fixtures').mkdir(mode=0o700)
        cls.prefixes=('core','kai_master_bridge','bridge_auth_012')
        cls.old_modules={name:module for name,module in sys.modules.items() if any(name==p or name.startswith(p+'.') for p in cls.prefixes)}
        for name in cls.old_modules:sys.modules.pop(name)
        cls.old_path=list(sys.path)
        sys.path[:0]=[str(cls.copy),str(cls.copy/'isolated_bridge'),str(cls.copy/'isolated_LF')]
        cls.auth=importlib.import_module('bridge_auth_012')
        cls.model=importlib.import_module('core.loop_factory.model')
        cls.runner=importlib.import_module('core.loop_factory.runner')
        cls.store_module=importlib.import_module('core.loop_factory.store')
        cls.workers=importlib.import_module('core.loop_factory.workers')
        cls.contracts=importlib.import_module('kai_master_bridge.contracts')
        cls.ledger_module=importlib.import_module('kai_master_bridge.ledger')

    @classmethod
    def tearDownClass(cls):
        unchanged=all(hashlib.sha256((SOURCE/path).read_bytes()).hexdigest()==sha for path,sha in cls.hashes.items())
        target=os.environ.get('KAI_MESHY_LF_TEST_EVIDENCE')
        if target:
            Path(target).write_text(json.dumps({'scope':'EXISTING_GUARDED_RUNNER_WITH_EPHEMERAL_LAB_AUTH; NOT_OWNER_AUTHENTICATION',
                 'copied_python_sources':cls.hashes,'original_sources_unchanged':unchanged,
                 'source':str(SOURCE),'authority':'LOCAL_LAB_CONTROL_NOT_AUTHENTICATED_REMOTE',
                 'new_gateway_or_service':False,'historical_lease_renewed':False,'scenarios':SCENARIOS},indent=2))
        for name in list(sys.modules):
            if any(name==p or name.startswith(p+'.') for p in cls.prefixes):sys.modules.pop(name)
        sys.modules.update(cls.old_modules);sys.path[:]=cls.old_path
        cls.parent.cleanup()
        if not unchanged:raise AssertionError('Original guarded source changed during fixture test')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='mesh-observe-',dir=self.copy/'fixtures')
        self.root=Path(self.temp.name);self.state=self.root/'owner_bridge_state';self.case_db=self.root/'case.sqlite3'
        self.case='synthetic-meshy-observation'
        with closing(sqlite3.connect(self.case_db)) as db:
            db.execute(CASE_SCHEMA);db.execute('INSERT INTO case_control VALUES(?,?,?,?,?)',(self.case,'RUNNING',0,'','synthetic'));db.commit()
        self.store=self.store_module.LoopStore(self.root/'lf.sqlite3');self.store.initialize()
        self.forge=Forge(self.root/'forge',cli=NoVendor())
        source=self.forge.root/'source.png'
        Image.frombytes('RGB',(64,64),random.Random(2).randbytes(64*64*3)).save(source)
        self.forge.create_job('AHU',source,budget=36)
        self.reader=CountingForge(self.forge);self.worker_instances=[]
        self.auth.provision_lab_issuer(self.state)
        self.manifest,self.worker=self.make_job('MAIN')

    def make_job(self,suffix,dependencies=(),forge_job_id='AHU'):
        manifest=make_observation_manifest(self.forge.get_job(forge_job_id),lf_model=self.model,
                    authority_refs=['doc:KAI_MESHY_FORGE_CURRENT'],dependencies=dependencies)
        manifest.job_id='OBSERVE_'+suffix
        sandbox=self.root/('sandbox-'+suffix)
        # Explicit new disposable scope; no active envelope or historical job is altered.
        manifest.write_scope=[str(sandbox)]
        self.store.create_job(manifest)
        worker=ForgeObservationWorker(self.reader,forge_job_id,sandbox,loop_store=self.store,
                    outcome_type=self.workers.StepOutcome,fence_type=self.auth.VerifiedBridgeLease)
        self.worker_instances.append(worker)
        return manifest,worker

    def issue(self,manifest=None,worker=None,approve=True,worker_id=None):
        manifest=manifest or self.manifest;worker=worker or self.worker
        raw={'schema':self.contracts.SCHEMA,'request_id':str(uuid4()),'node_id':'lab012','capability':'lab.loop.dispatch',
             'params':{'case_id':self.case,'job_id':manifest.job_id,'worker_id':worker_id or worker.worker_id,
                       'sandbox':str(worker.sandbox),'epoch':0},'deadline':int(time.time())+75}
        action=self.contracts.Action.parse(raw)
        if approve:self.ledger_module.Ledger(self.state/'master.sqlite3').add_approval(action.request_id,action.digest(),actor='local-owner',ttl=60)
        return self.auth.synthetic_issue(self.state,self.case_db,raw,ttl_seconds=50)

    def execute(self,manifest=None,worker=None,after_checkpoint=None):
        manifest=manifest or self.manifest;worker=worker or self.worker
        return self.runner.LoopRunner(self.store,{worker.worker_id:worker}).run_once(
            manifest.job_id,branch='feat/kai-meshy-observation-lab',worker_id=worker.worker_id,after_checkpoint=after_checkpoint)

    def counts(self):
        return tuple(self.store.connection.execute('SELECT count(*) FROM '+table).fetchone()[0]
                     for table in ('attempts','step_receipts','checkpoints','evidence'))

    def control(self,mode,epoch):
        with closing(sqlite3.connect(self.case_db)) as db:
            db.execute('UPDATE case_control SET mode=?,epoch=? WHERE case_id=?',(mode,epoch,self.case));db.commit()

    def reopen(self):
        self.store.close();self.store=self.store_module.LoopStore(self.root/'lf.sqlite3');self.store.initialize()
        for worker in self.worker_instances:worker.loop_store=self.store

    def tearDown(self):
        SCENARIOS.append({'name':self._testMethodName,'counts_attempt_receipt_checkpoint_evidence':self.counts(),
                          'domain_get_job_calls':self.reader.reads,'worker_completed_calls':sum(w.run_calls for w in self.worker_instances),
                          'vendor_requests':self.forge.cli.calls,'scope':'NEW_EPHEMERAL_FIXTURE_ONLY'})
        self.store.close();self.temp.cleanup()

    def test_real_runner_creates_receipt_checkpoint_and_resume_does_not_rerun(self):
        self.issue();self.assertEqual(self.manifest.state.value,'QUEUED')
        self.assertEqual(self.execute().state.value,'SUCCEEDED')
        self.assertEqual(self.counts(),(1,1,1,1));self.assertEqual(self.worker.run_calls,1)
        self.reopen();self.assertEqual(self.execute().state.value,'SUCCEEDED')
        self.assertEqual(self.counts(),(1,1,1,1));self.assertEqual(self.worker.run_calls,1)
        self.assertEqual(self.reader.reads,1);self.assertEqual(self.forge.cli.calls,0)
        content=self.worker.output_path().read_text()
        self.assertIn('NOT_A_RECEIPT',content);self.assertNotIn(str(self.root),content)

    def test_generic_planned_operation_real_runner_receipt_and_idempotent_resume(self):
        engine=CapabilityEngine(self.forge)
        planned=engine.create_operation('FREE_GENERIC','text_to_3d.preview',
                    {'prompt':'new isolated free infrastructure observation'},budget=36)
        self.assertEqual(planned['status'],'PLANNED')
        self.assertEqual(planned['reservation'],0);self.assertIsNone(planned['task_id'])
        manifest,worker=self.make_job('GENERIC',forge_job_id='FREE_GENERIC')
        self.issue(manifest,worker)
        self.assertEqual(self.execute(manifest,worker).state.value,'SUCCEEDED')
        self.assertEqual(self.counts(),(1,1,1,1));self.assertEqual(self.reader.reads,1)
        body=json.loads(worker.output_path().read_text())
        self.assertEqual(body['projection']['schema'],'kai.meshy.loop-observation/2')
        self.assertEqual(body['projection']['stages'][0]['stage'],'op:main')
        self.assertEqual(body['projection']['stages'][0]['status'],'PLANNED')
        self.assertLessEqual(worker.output_path().stat().st_size,32768)
        self.assertNotIn('infrastructure observation',worker.output_path().read_text())
        self.reopen()
        self.assertEqual(self.execute(manifest,worker).state.value,'SUCCEEDED')
        self.assertEqual(self.counts(),(1,1,1,1));self.assertEqual(self.reader.reads,1)
        self.assertEqual(worker.run_calls,1);self.assertEqual(self.forge.cli.calls,0)
        self.assertEqual(engine.get_operation('FREE_GENERIC')['status'],'PLANNED')

    def test_crash_after_real_checkpoint_recovers_without_second_observation(self):
        self.issue()
        def crash():raise RuntimeError('INJECTED_AFTER_REAL_CHECKPOINT')
        with self.assertRaisesRegex(RuntimeError,'INJECTED_AFTER_REAL_CHECKPOINT'):self.execute(after_checkpoint=crash)
        self.assertEqual(self.counts()[:3],(1,1,1));self.assertEqual(self.reader.reads,1)
        self.reopen();self.assertEqual(self.execute().state.value,'SUCCEEDED')
        self.assertEqual(self.worker.run_calls,1);self.assertEqual(self.reader.reads,1)
        self.assertEqual(self.counts(),(1,1,1,1))

    def test_missing_lease_denies_before_attempt_or_domain_read(self):
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.counts(),(0,0,0,0));self.assertEqual(self.reader.reads,0)

    def test_lease_without_synthetic_approval_is_denied(self):
        with self.assertRaises(self.auth.AuthDenied):self.issue(approve=False)
        self.assertEqual(self.counts(),(0,0,0,0))

    def test_wrong_signed_worker_scope_is_denied(self):
        self.issue(worker_id='different-observer')
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.counts(),(0,0,0,0));self.assertEqual(self.reader.reads,0)

    def test_stop_all_after_issue_denies_without_observation(self):
        self.issue();(self.state/'STOP_ALL').write_text('LAB STOP')
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.counts(),(0,0,0,0));self.assertEqual(self.reader.reads,0)

    def test_changed_case_epoch_denies_without_renewing_historical_lease(self):
        self.issue();self.control('RUNNING',1)
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.counts(),(0,0,0,0));self.assertEqual(self.reader.reads,0)

    def test_completed_receipt_after_stop_is_preserved_but_execution_not_reauthorized(self):
        self.issue();self.execute();before=self.counts();self.control('PAUSED',1)
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.counts(),before);self.assertEqual(self.worker.run_calls,1)

    def test_queued_dependency_blocks_before_dispatch_and_guarded_worker(self):
        dependency,_=self.make_job('DEPENDENCY')
        manifest,worker=self.make_job('DEP_BLOCKED',[dependency.job_id])
        with self.assertRaisesRegex(ForgeError,'DEPENDENCY_NOT_SUCCEEDED'):worker.assert_dependencies(manifest)
        self.assertEqual(self.counts(),(0,0,0,0))
        self.issue(manifest,worker);self.execute(manifest,worker)
        self.assertEqual(self.counts()[1],0);self.assertEqual(self.reader.reads,0)
        self.assertFalse(worker.output_path().exists())

    def test_actual_succeeded_dependency_allows_observer_with_real_receipts(self):
        dependency,dep_worker=self.make_job('DEPENDENCY')
        self.issue(dependency,dep_worker);self.assertEqual(self.execute(dependency,dep_worker).state.value,'SUCCEEDED')
        manifest,worker=self.make_job('DEPENDENT',[dependency.job_id])
        worker.assert_dependencies(manifest);self.issue(manifest,worker)
        self.assertEqual(self.execute(manifest,worker).state.value,'SUCCEEDED')
        self.assertEqual(self.counts(),(2,2,2,2));self.assertEqual(self.forge.cli.calls,0)

    def test_tampered_artifact_cannot_be_promoted_or_reexecuted(self):
        self.issue();self.execute();self.worker.output_path().write_text('tampered')
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.worker.run_calls,1);self.assertEqual(self.reader.reads,1)

    def test_fake_fence_and_unguarded_entrypoint_are_denied(self):
        context=types.SimpleNamespace(job=self.manifest,sandbox=self.worker.sandbox,input_hash='f'*64)
        with self.assertRaisesRegex(ForgeError,'GUARDED_RUNNER'):self.worker.run(context)
        with self.assertRaisesRegex(ForgeError,'FENCE_TYPE_REQUIRED'):
            self.worker.run_guarded(context,types.SimpleNamespace(require=lambda *args:True))
        self.assertEqual(self.reader.reads,0)


if __name__=='__main__':unittest.main()
