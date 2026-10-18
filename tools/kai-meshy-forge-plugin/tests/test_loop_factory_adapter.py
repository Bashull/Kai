"""Offline, no-store connector tests against the existing LF model source."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import types
import unittest

from kai_meshy.core import ForgeError
from kai_meshy.loop_factory_adapter import MODEL_SHA256, make_observation_manifest, observation_projection

SOURCE=Path(os.environ.get('KAI_LOOP_FACTORY_SOURCE',str(Path.home()/'KAI_ONE_MIND_LAB/F00_20261014/loop_factory_cell000_checkout/core/loop_factory/model.py')))


def fixture():
    return {'job':{'id':'AHU','source_sha':'a'*64,'budget':36,'preview_approved':0,'local_cancelled':0,'rejected':1,
                   'source':'/private/original.png','approved_actor':'private actor'},
            'stages':[{'stage':'prototype','status':'SUCCEEDED','task_id':'01a15090-2515-7561-99e8-14def9e4b0ea',
                       'reservation':6,'actual':6,'payload':'must not leave','image_url':'https://private/?Signature=fixture'}]}


class ProjectionTests(unittest.TestCase):
    def test_projection_excludes_private_paths_urls_payloads_and_actors(self):
        encoded=json.dumps(observation_projection(fixture()))
        for text in ('/private','https://','Signature','must not leave','private actor'):
            self.assertNotIn(text,encoded)
        self.assertIn('NOT_A_VENDOR_OR_LOOP_FACTORY_RECEIPT',encoded)

    def test_invalid_state_or_credit_never_becomes_observation(self):
        snapshot=fixture();snapshot['stages'][0]['actual']=float('nan')
        with self.assertRaises(ForgeError):observation_projection(snapshot)

    def test_generic_stage_uses_schema2_without_paths_request_or_capability_values(self):
        snapshot=fixture();snapshot['stages']=[{'stage':'op:main','status':'PLANNED','task_id':None,
              'reservation':0,'actual':None,'request_json':'private','manifest_path':'/private',
              'capability_id':'untrusted value https://private','contract_sha':'untrusted'}]
        value=observation_projection(snapshot)
        self.assertEqual(value['schema'],'kai.meshy.loop-observation/2')
        self.assertEqual(value['stages'][0]['stage'],'op:main')
        self.assertNotIn('private',json.dumps(value));self.assertNotIn('untrusted',json.dumps(value))

    def test_legacy_projection_keeps_exact_schema1_contract(self):
        value=observation_projection(fixture())
        self.assertEqual(value['schema'],'kai.meshy.loop-observation/1')
        self.assertEqual(set(value['stages'][0]),{'stage','status','task_id','reserved_meshy_credits','actual_meshy_credits'})

    def test_generic_namespace_planned_facts_and_total_stages_are_bounded(self):
        for name in ('op:../private','op:','op:'+('x'*71),'op:main/other'):
            snapshot=fixture();snapshot['stages']=[{'stage':name,'status':'PLANNED'}]
            with self.assertRaises(ForgeError):observation_projection(snapshot)
        for bad in ({'task_id':'00000000-0000-0000-0000-000000000001'},{'reservation':1},{'actual':1}):
            snapshot=fixture();snapshot['stages']=[{'stage':'op:main','status':'PLANNED',**bad}]
            with self.assertRaises(ForgeError):observation_projection(snapshot)
        snapshot=fixture();snapshot['stages']=[{'stage':'op:step_'+str(i),'status':'PLANNED'} for i in range(64)]
        self.assertEqual(len(observation_projection(snapshot)['stages']),64)
        snapshot['stages'].append({'stage':'op:step_64','status':'PLANNED'})
        with self.assertRaises(ForgeError):observation_projection(snapshot)
        snapshot=fixture();snapshot['stages'].append(copy.deepcopy(snapshot['stages'][0]))
        with self.assertRaises(ForgeError):observation_projection(snapshot)


@unittest.skipUnless(SOURCE.is_file(),'Existing Loop Factory model source not available in this environment')
class ExistingLoopFactoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=SOURCE.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=MODEL_SHA256:
            raise AssertionError('Existing Loop Factory contract hash drifted; review before adaptation')
        # Audited model consists of standard-library contracts only. Compile in
        # memory to avoid writing __pycache__ or changing the donor checkout.
        cls.model=types.ModuleType('_kai_meshy_existing_lf_contract')
        sys.modules[cls.model.__name__]=cls.model
        exec(compile(raw,str(SOURCE),'exec'),cls.model.__dict__)

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop(cls.model.__name__,None)

    def build(self,snapshot=None,**kwargs):
        return make_observation_manifest(snapshot or fixture(),lf_model=self.model,
                                         authority_refs=['drive:current-authority','git:9ba6179'],**kwargs)

    def test_real_contract_roundtrip_is_queued_a0_zero_eur_no_receipt(self):
        manifest=self.build();data=manifest.to_dict()
        self.assertIsInstance(manifest,self.model.JobManifest)
        self.assertEqual(data['state'],'QUEUED');self.assertEqual(data['attempt'],0)
        self.assertEqual(data['autonomy_level'],'A0');self.assertEqual(data['budget']['max_cost_eur'],0)
        self.assertEqual(data['budget']['currency'],'EUR');self.assertEqual(data['budget']['max_retries'],0)
        self.assertEqual(data['write_scope'],[]);self.assertEqual(data['evidence_refs'],[])
        self.assertEqual(data['allowed_tools'],['kai_meshy_get_job']);self.assertIsNone(data['worker'])

    def test_same_observation_has_stable_identity_and_state_change_does_not_collide(self):
        first=self.build().job_id;snapshot=fixture();snapshot['job']['source']='/different/private/path'
        self.assertEqual(self.build(snapshot).job_id,first)
        snapshot['stages'][0]['status']='SUBMISSION_UNKNOWN'
        self.assertNotEqual(self.build(snapshot).job_id,first)

    def test_dependency_ids_pass_through_without_claiming_resolution(self):
        manifest=self.build(dependencies=['EXISTING_REFERENCE_QA'])
        self.assertEqual(manifest.dependencies,['EXISTING_REFERENCE_QA'])
        self.assertEqual(manifest.evidence_refs,[])

    def test_no_secret_authority_or_paths_can_be_smuggled_as_dependencies(self):
        with self.assertRaises(ForgeError):
            make_observation_manifest(fixture(),lf_model=self.model,authority_refs=['https://private/?token=fixture'])
        with self.assertRaises(ForgeError):
            self.build(dependencies=['/private/database.sqlite3'])


if __name__=='__main__':unittest.main()
