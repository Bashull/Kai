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
