"""Independent contract+engine boundaries; vendor is an in-memory fake only."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from kai_meshy.capability_engine import CapabilityEngine
from kai_meshy.contracts import CapabilityCatalog
from kai_meshy.core import Forge, ForgeError


class ReviewVendor:
    def __init__(self):
        self.tasks = {}; self.posts = []; self.pages = {}; self.gets = []; self.lost_reply = False

    def auth(self): return {'authenticated': True, 'verified': True}
    def balance(self): return {'balance': 999}

    @staticmethod
    def envelope(body):
        return {'schema_version': 'v1', 'ok': True, 'result': {'http_status': 200, 'method': 'GET', 'path': '/synthetic', 'body': body}}

    def request(self, contract, action, *, payload=None, task_id=None, query=None, **kwargs):
        if action == 'create':
            task_id = '00000000-0000-0000-0000-' + str(len(self.posts)+1).zfill(12)
            self.posts.append((contract['id'], copy.deepcopy(payload)))
            self.tasks[task_id] = {'id': task_id, 'status': 'IN_PROGRESS', 'consumed_credits': 0,
                                   'name': payload.get('name'), 'progress': 0}
            if self.lost_reply: raise ForgeError('FAKE_LOST_REPLY')
            return self.envelope({'result': task_id})
        if action == 'get':
            self.gets.append(task_id)
            return self.envelope(copy.deepcopy(self.tasks[task_id]))
        if action == 'list':
            return self.envelope(copy.deepcopy(self.pages.get((query or {}).get('page_num', 1), [])))
        raise AssertionError('UNEXPECTED_FAKE_ACTION')


class IndependentGeneralBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.refs = self.root/'refs'; self.refs.mkdir()
        source = io.BytesIO(); Image.new('RGB', (64,64), (70,70,70)).save(source, format='PNG')
        self.source = self.refs/'source.png'; self.source.write_bytes(source.getvalue()+b'\0'*2048)
        self.vendor = ReviewVendor(); self.catalog = CapabilityCatalog()
        self.forge = Forge(self.root/'forge', self.vendor, reference_roots=[self.refs],
                           spending_enabled=True, spending_job_ids={'REVIEW'}, max_credits=500)
        self.engine = CapabilityEngine(self.forge, self.catalog)

    def plan(self, capability='text_to_3d.preview', operation='parent', parameters=None):
        return self.engine.create_operation('REVIEW', capability,
            parameters if parameters is not None else {'prompt': 'offline review cube'},
            operation_id=operation, budget=500)

    def succeeded(self, operation='parent'):
        task = self.engine.submit_operation('REVIEW', operation)['task_id']
        self.vendor.tasks[task].update(status='SUCCEEDED', consumed_credits=20, progress=100)
        self.engine.refresh_operation('REVIEW', operation)
        return task

    def test_rig_task_must_be_rigging_family_before_any_child_post(self):
        self.plan(); self.succeeded()
        try:
            self.plan('animation.create', 'child', {'rig_task_id': {'task_from_operation': 'parent'}, 'action_id': 0})
            with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW', 'child')
        except ForgeError:
            pass  # Rejecting the incompatible plan itself is stricter and safe.
        self.assertEqual(len(self.vendor.posts), 1)

    def test_refine_task_must_be_text_preview_family_before_any_child_post(self):
        self.plan('creative_lab.brick_figure.prototype', parameters={'image_url': {'local_path': str(self.source)}})
        self.succeeded()
        try:
            self.plan('text_to_3d.refine', 'child', {'preview_task_id': {'task_from_operation': 'parent'}})
            with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW', 'child')
        except ForgeError:
            pass
        self.assertEqual(len(self.vendor.posts), 1)

    def test_succeeded_prototype_still_requires_visual_approval(self):
        self.plan('creative_lab.brick_figure.prototype', parameters={'image_url': {'local_path': str(self.source)}})
        self.succeeded()
        self.plan('creative_lab.brick_figure.build', 'child', {'input_task_id': {'task_from_operation': 'parent'}})
        with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW', 'child')
        self.assertEqual(len(self.vendor.posts), 1)

    def test_rejected_ahu_is_not_a_generic_build_authorization(self):
        self.plan()
        with self.forge._db() as db: db.execute('UPDATE jobs SET rejected=1 WHERE id="REVIEW"')
        with self.assertRaises(ForgeError): self.plan('creative_lab.brick_figure.build', 'child', {'input_task_id':'01a15090-2515-7561-99e8-14def9e4b0ea'})
        self.assertEqual(self.vendor.posts, [])

    def test_unknown_outcome_preserves_reservation_and_does_not_repeat(self):
        self.plan(); self.vendor.lost_reply = True
        with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW', 'parent')
        first = self.engine.get_operation('REVIEW', 'parent')
        self.assertEqual(first['status'], 'SUBMISSION_UNKNOWN'); self.assertGreater(first['reservation'], 0)
        with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW', 'parent')
        self.assertEqual(len(self.vendor.posts), 1)
        task = next(iter(self.vendor.tasks)); self.vendor.tasks[task]['name'] = 'wrong-managed-name'
        with self.assertRaises(ForgeError): self.engine.reconcile_operation('REVIEW', 'parent', task, first['request_sha'])
        self.assertEqual(self.engine.get_operation('REVIEW', 'parent')['status'], 'SUBMISSION_UNKNOWN')
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'], first['reservation'])

    def test_full_array_page_is_not_false_complete_history(self):
        def task(number): return {'id': '00000000-0000-0000-0000-'+str(number).zfill(12), 'status':'SUCCEEDED'}
        self.vendor.pages = {1:[task(1),task(2)], 2:[task(3)]}
        result = self.engine.list_history('text_to_3d.preview', page_size=2)
        count = sum(len(page['tasks']) for page in result['pages'])
        self.assertTrue(count == 3 or result['complete_history'] is False, 'Missing page falsely declared complete')

    def test_invalid_many_references_are_denied_before_copy(self):
        items = [{'local_path': str(self.source)}] * 100
        with patch.object(self.engine, '_copy_reference', side_effect=AssertionError('MEDIA_COPIED_BEFORE_CARDINALITY_CHECK')) as copied:
            with self.assertRaises(ForgeError): self.plan('multi_image_to_3d.generate', parameters={'image_urls': items})
        self.assertEqual(copied.call_count, 0)

    def test_expired_pricing_cannot_remain_exact_spend_gate(self):
        result = self.catalog.quote('creative_lab.brick_figure.build', {'input_task_id':'00000000-0000-0000-0000-000000000001'}, as_of='2099-01-01')
        self.assertFalse(result['spend_allowed']); self.assertNotEqual(result['price_status'], 'EXACT')

    def test_expired_remote_parent_blocks_child_without_replacing_parent(self):
        self.plan(); self.succeeded()
        self.plan('rigging.create','rig',{'input_task_id':{'task_from_operation':'parent'}})
        rig=self.succeeded('rig')
        self.vendor.tasks[rig]['expires_at']=1
        self.plan('animation.create','child',{'rig_task_id':{'task_from_operation':'rig'},'action_id':0})
        with self.assertRaises(ForgeError): self.engine.submit_operation('REVIEW','child')
        self.assertEqual(len(self.vendor.posts),2)
        self.assertEqual(self.engine.get_operation('REVIEW','rig')['task_id'],rig)

    def test_operator_zero_ceiling_denies_nonzero_quote_before_auth_or_post(self):
        self.plan()
        engine=CapabilityEngine(self.forge,self.catalog,max_operation_credits=0)
        with patch.object(self.vendor,'auth',side_effect=AssertionError('AUTH_BEFORE_CEILING')):
            with self.assertRaises(ForgeError):engine.submit_operation('REVIEW','parent')
        self.assertEqual(self.vendor.posts,[])
        row=engine.get_operation('REVIEW','parent')
        self.assertEqual(row['status'],'PLANNED');self.assertEqual(row['reservation'],0)
        self.assertIsNone(row['task_id'])

    def test_special_output_paths_and_variants_stay_on_allowed_cdn(self):
        url='https://assets.meshy.ai/synthetic/output.glb'
        self.assertEqual(self.engine._asset_url({'result':{'rigged_character_glb_url':url}},'glb'),url)
        self.assertEqual(self.engine._asset_url({'result':{'animation_glb_url':url}},'glb'),url)
        task={'result':{'basic_animations':{'walking_glb_url':url}}}
        self.assertEqual(self.engine._asset_url(task,'glb',variant='walking_glb'),url)
        with self.assertRaises(ForgeError):self.engine._asset_url(task,'fbx',variant='walking_glb')
        with self.assertRaises(ForgeError):self.engine._asset_url(task,'glb',variant='../../private')
        with self.assertRaises(ForgeError):self.engine._asset_url({'result':{'animation_glb_url':'https://127.0.0.1/private'}},'glb')


if __name__ == '__main__': unittest.main()
