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


class AnimationReviewVendor(ReviewVendor):
    def __init__(self):
        super().__init__()
        self.library_reads = []; self.library_failure = False
        self.library = [{'action_id':n, 'name':'Synthetic action '+str(n), 'key':'synthetic-'+str(n),
                         'category':'DailyActions', 'sub_category':'Review'} for n in (0,331,333)]

    def request(self, contract, action, **kwargs):
        if contract.get('routes',{}).get('get') == '/openapi/v1/animations/library':
            if action != 'get' or any(kwargs.get(k) is not None for k in ('task_id','payload','query')):
                raise AssertionError('LIBRARY_REQUEST_WAS_NOT_FIXED_GET')
            self.library_reads.append({'method':'GET','path':'/animations/library','timeout':kwargs.get('timeout')})
            if self.library_failure:raise ForgeError('SIMULATED_LIBRARY_READ_FAILURE')
            return {'schema_version':'meshy.cli/v1','ok':True,'command':'api','result':{
                'http_status':200,'method':'GET','path':'/animations/library','api':'v1','body':copy.deepcopy(self.library)}}
        return super().request(contract,action,**kwargs)


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

    def test_generic_price_expiring_during_auth_keeps_plan_unreserved(self):
        from datetime import datetime,timedelta,timezone
        self.plan();clock=[datetime.now(timezone.utc).date()]
        def slow_auth():
            clock[0]+=timedelta(days=1000)
            return {'authenticated':True,'verified':True}
        with patch('kai_meshy.contracts._day',side_effect=lambda value:clock[0]),patch.object(self.vendor,'auth',side_effect=slow_auth):
            with self.assertRaises(ForgeError):self.engine.submit_operation('REVIEW','parent')
        row=self.engine.get_operation('REVIEW','parent')
        self.assertEqual(row['status'],'PLANNED');self.assertEqual(row['reservation'],0)
        self.assertIsNone(row['task_id']);self.assertEqual(self.vendor.posts,[])

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


class AnimationMembershipSubmitBoundaries(unittest.TestCase):
    # Reuse fixture/helpers without rerunning unrelated probes a second time.
    setUp=IndependentGeneralBoundaries.setUp
    plan=IndependentGeneralBoundaries.plan
    succeeded=IndependentGeneralBoundaries.succeeded
    def _rigged(self, parameters):
        self.vendor=AnimationReviewVendor();self.forge.cli=self.vendor
        self.plan();self.succeeded()
        self.plan('rigging.create','rig',{'input_task_id':{'task_from_operation':'parent'}})
        self.succeeded('rig')
        self.plan('animation.create','animation',{'rig_task_id':{'task_from_operation':'rig'},**parameters})

    def _unsubmitted(self):
        row=self.engine.get_operation('REVIEW','animation')
        self.assertEqual(row['status'],'PLANNED');self.assertEqual(row['reservation'],0)
        self.assertIsNone(row['task_id']);self.assertIsNone(row['request_sha'])
        self.assertEqual(len(self.vendor.posts),2)
        with self.forge._db() as db:
            details=[json.loads(r['detail']) for r in db.execute('SELECT detail FROM audit_events WHERE event="OPERATION_SUBMISSION_INTENT"')]
        self.assertFalse(any(d['operation_id']=='animation' for d in details))

    def test_animation_missing_332_denies_before_auth_intent_or_post(self):
        self._rigged({'action_id':332})
        with patch.object(self.vendor,'auth',side_effect=AssertionError('AUTH_BEFORE_LIBRARY_MEMBERSHIP')):
            with self.assertRaises(ForgeError):self.engine.submit_operation('REVIEW','animation')
        self._unsubmitted();self.assertEqual(len(self.vendor.library_reads),1)

    def test_animation_mixed_action_list_denies_entire_submission(self):
        self._rigged({'action_ids':[0,332]})
        with self.assertRaises(ForgeError):self.engine.submit_operation('REVIEW','animation')
        self._unsubmitted();self.assertEqual(len(self.vendor.library_reads),1)

    def test_animation_library_read_failure_does_not_reserve_or_fallback(self):
        self._rigged({'action_id':0});self.vendor.library_failure=True
        with self.assertRaises(ForgeError):self.engine.submit_operation('REVIEW','animation')
        self._unsubmitted();self.assertEqual(len(self.vendor.library_reads),1)

    def test_animation_valid_actions_bind_library_receipt_without_rest_parameter(self):
        self._rigged({'action_ids':[0,333]})
        submitted=self.engine.submit_operation('REVIEW','animation')
        self.assertEqual(submitted['status'],'PENDING');self.assertEqual(submitted['reservation'],6)
        self.assertEqual(len(self.vendor.library_reads),1)
        payload=self.vendor.posts[-1][1]
        self.assertEqual(payload['action_ids'],[0,333]);self.assertNotIn('animation_library',payload)
        self.assertFalse(any('library' in key for key in payload))
        proof=submitted['quote']['animation_library']
        self.assertEqual(proof['action_ids'],[0,333]);self.assertEqual(proof['action_count'],3)
        self.assertEqual(len(proof['fingerprint_sha256']),64)
        with self.forge._db() as db:
            details=[json.loads(r['detail']) for r in db.execute('SELECT detail FROM audit_events WHERE event="OPERATION_SUBMISSION_INTENT"')]
        intent=next(d for d in details if d['operation_id']=='animation')
        self.assertEqual(intent['animation_library_fingerprint'],proof['fingerprint_sha256'])
        self.assertEqual(intent['animation_action_ids'],[0,333]);self.assertEqual(intent['request_sha'],submitted['request_sha'])

    def test_animation_zero_ceiling_and_disabled_policy_do_not_fetch_library(self):
        self._rigged({'action_id':0})
        zero=CapabilityEngine(self.forge,self.catalog,max_operation_credits=0)
        with self.assertRaisesRegex(ForgeError,'OPERATOR_CEILING'):zero.submit_operation('REVIEW','animation')
        self.assertEqual(self.vendor.library_reads,[]);self._unsubmitted()
        self.forge.spending_enabled=False
        with self.assertRaisesRegex(ForgeError,'SPENDING_DISABLED'):self.engine.submit_operation('REVIEW','animation')
        self.assertEqual(self.vendor.library_reads,[]);self._unsubmitted()
        self.forge.spending_enabled=True;self.forge.spending_job_ids=frozenset()
        before_gets=len(self.vendor.gets)
        with self.assertRaisesRegex(ForgeError,'JOB_NOT_AUTHORIZED'):self.engine.submit_operation('REVIEW','animation')
        self.assertEqual(len(self.vendor.gets),before_gets);self.assertEqual(self.vendor.library_reads,[])

    def test_animation_snapshot_expiring_during_auth_rolls_back_before_intent(self):
        from datetime import datetime,timedelta,timezone
        self._rigged({'action_id':0});start=datetime.now(timezone.utc);clock=[start]
        def slow_auth():
            clock[0]=start+timedelta(seconds=301)
            return {'authenticated':True,'verified':True}
        with patch('kai_meshy.animation_library._utc_now',side_effect=lambda:clock[0]),patch.object(self.vendor,'auth',side_effect=slow_auth):
            with self.assertRaisesRegex(ForgeError,'STALE_OR_FUTURE'):self.engine.submit_operation('REVIEW','animation')
        self._unsubmitted();self.assertEqual(len(self.vendor.library_reads),1)

    def test_animation_motion_unknown_quote_does_not_fetch_preset_library(self):
        self._rigged({'action_id':0})
        self.plan('text_to_motion.generate','motion',{'prompt':'offline review motion','duration':3})
        self.succeeded('motion')
        self.plan('animation.create','retarget',{'rig_task_id':{'task_from_operation':'rig'},'motion_task_id':{'task_from_operation':'motion'}})
        with self.assertRaisesRegex(ForgeError,'EXACT_VERIFIED_PRICE'):self.engine.submit_operation('REVIEW','retarget')
        self.assertEqual(self.vendor.library_reads,[]);self.assertEqual(len(self.vendor.posts),3)

    def test_animation_live_678_cache_332_gap_is_membership_not_numeric_range(self):
        self._rigged({'action_id':332})
        cache=Path(__file__).parent/'fixtures/animation_library_20261018_safe.json'
        safe=json.loads(cache.read_text());self.vendor.library=copy.deepcopy(safe['items'])
        self.assertEqual(len(self.vendor.library),678)
        with self.assertRaises(ForgeError):self.engine.submit_operation('REVIEW','animation')
        self._unsubmitted()
        self.plan('animation.create','known',{ 'rig_task_id':{'task_from_operation':'rig'},'action_id':0})
        proof=self.engine.submit_operation('REVIEW','known')['quote']['animation_library']
        self.assertEqual(proof['action_count'],678);self.assertEqual(proof['action_ids'],[0])


class LegacyPriceReviewVendor(ReviewVendor):
    def __init__(self):super().__init__();self.api_calls=[]

    def api(self,method,path,payload=None):
        self.api_calls.append((method,path))
        if method=='POST':return self.request({'id':'legacy-brick'},'create',payload=payload)
        if method=='GET':return copy.deepcopy(self.tasks[path.rsplit('/',1)[-1]])
        raise AssertionError('UNEXPECTED_LEGACY_VERB')


class LegacyCurrentPriceBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.png'
        data=io.BytesIO();Image.new('RGB',(64,64),(70,70,70)).save(data,format='PNG')
        self.source.write_bytes(data.getvalue()+b'\0'*2048)
        self.vendor=LegacyPriceReviewVendor()
        self.forge=Forge(self.root/'forge',self.vendor,reference_roots=[self.root],spending_enabled=True,
                         spending_job_ids={'PRICE'},max_credits=40)
        self.forge.create_job('PRICE',self.source,budget=40)

    def _no_intent(self):
        self.assertEqual(self.vendor.posts,[])
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],0)
        with self.forge._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM stages').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM audit_events WHERE event="SUBMISSION_INTENT"').fetchone()[0],0)

    def test_legacy_expired_quote_denies_before_auth_or_intent(self):
        original=CapabilityCatalog.quote
        def stale(catalog,op,payload):return original(catalog,op,payload,as_of='2099-01-01')
        with patch.object(CapabilityCatalog,'quote',stale),patch.object(self.vendor,'auth',side_effect=AssertionError('AUTH_BEFORE_PRICE_CHECK')):
            with self.assertRaisesRegex(ForgeError,'LEGACY_PRICE_REVALIDATION_REQUIRED'):self.forge.submit('PRICE','prototype')
        self._no_intent()

    def test_legacy_unknown_changed_and_failed_catalogue_do_not_use_hardcoded_fallback(self):
        for response in [{'credits':None,'price_status':'UNKNOWN','spend_allowed':False},
                         {'credits':7,'price_status':'EXACT','spend_allowed':True}]:
            with self.subTest(response=response),patch.object(CapabilityCatalog,'quote',return_value=response):
                with self.assertRaisesRegex(ForgeError,'LEGACY_PRICE_REVALIDATION_REQUIRED'):self.forge.submit('PRICE','prototype')
            self._no_intent()
        with patch.object(CapabilityCatalog,'quote',side_effect=ForgeError('CATALOGUE_LOAD_FAILED')):
            with self.assertRaisesRegex(ForgeError,'LEGACY_PRICE_REVALIDATION_REQUIRED'):self.forge.submit('PRICE','prototype')
        self._no_intent()

    def test_legacy_rechecks_quote_inside_reservation_transaction(self):
        real=CapabilityCatalog().quote('creative_lab.brick_figure.prototype',{'image_url':'data:image/png;base64,iVBORw0KGgo='})
        with patch.object(CapabilityCatalog,'quote',side_effect=[real,{'credits':None,'price_status':'UNKNOWN','spend_allowed':False}]):
            with self.assertRaisesRegex(ForgeError,'LEGACY_PRICE_REVALIDATION_REQUIRED'):self.forge.submit('PRICE','prototype')
        self._no_intent()

    def test_legacy_current_prototype6_build30_keep_routes_and_audit_price_proof(self):
        first=self.forge.submit('PRICE','prototype');task=first['task_id']
        self.vendor.tasks[task].update(status='SUCCEEDED',progress=100,consumed_credits=6)
        self.forge.refresh('PRICE','prototype')
        preview=self.forge.root/'jobs/PRICE/preview.png';preview.write_bytes(self.source.read_bytes())
        from kai_meshy.core import digest
        self.forge.approve('PRICE',digest(preview),actor='review-owner')
        second=self.forge.submit('PRICE','build')
        self.assertEqual((first['reserved_credits'],second['reserved_credits']),(6,30))
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],36)
        posts=[path for method,path in self.vendor.api_calls if method=='POST']
        self.assertEqual(posts,['/brick-figure/v1/prototype','/brick-figure/v1/build'])
        with self.forge._db() as db:
            intents=[json.loads(r['detail']) for r in db.execute('SELECT detail FROM audit_events WHERE event="SUBMISSION_INTENT" ORDER BY created')]
        import hashlib
        for detail,price in zip(intents,(6,30)):
            proof=detail['current_price_quote'];self.assertEqual(proof['quote']['credits'],price)
            self.assertEqual(proof['quote_sha256'],hashlib.sha256(json.dumps(proof['quote'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())
            self.assertEqual(len(proof['catalogue_sha256']),64);self.assertEqual(len(proof['request_fingerprint_sha256']),64)


if __name__ == '__main__': unittest.main()
