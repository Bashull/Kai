"""Generalized engine canaries use private temporary files and fake vendor only."""
import concurrent.futures
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import struct
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image
from kai_meshy.core import Forge, ForgeError, MeshyCLI, digest
from kai_meshy.capability_engine import CapabilityEngine


def png(color):
    out = io.BytesIO(); Image.new('RGB', (32,32), color).save(out, format='PNG')
    return out.getvalue() + b'\0' * 2048


class FakeCatalog:
    def __init__(self):
        self.operations = {}
        for name, price in [('image_to_3d.generate', 5), ('text_to_3d.preview', 5), ('remesh.create', 5),
                            ('creative_lab.brick_figure.prototype', 6), ('creative_lab.brick_figure.build', 30), ('unknown.create', None)]:
            version = 'creative-lab' if name.startswith('creative_lab') else 'v2' if name.startswith('text_') else 'v1'
            self.operations[name] = {'id': name, 'api_version': version, 'contract_version': 'test1',
                                    'routes': {'create': '/openapi/' + version + '/resource', 'get': '/openapi/' + version + '/resource/{task_id}', 'list': '/openapi/' + version + '/resource'},
                                    'route_methods': {'create':'POST','get':'GET','list':'GET'},
                                    'input_fields': {'image_url': {'kind':'image'}, 'input_task_id': {'kind':'task_id'}, 'model_url': {'kind':'model'}},
                                    'request_schema': {'properties': {k:{} for k in ['name','image_url','input_task_id','model_url','prompt','ai_model']}},
                                    'list_query_schema': {'properties': {'page_num':{'type':'integer','minimum':1},'page_size':{'type':'integer','minimum':1,'maximum':100}}},
                                    'test_price': price, 'parent_constraints': {}}
        self.operations['creative_lab.brick_figure.build']['parent_constraints'] = {
            'operation_id': 'creative_lab.brick_figure.prototype', 'status': 'SUCCEEDED', 'human_visual_gate': True}

    def describe(self, op):
        if op not in self.operations:
            raise ForgeError('CAPABILITY_NOT_FOUND')
        return copy.deepcopy(self.operations[op])

    def list(self):
        return [{'id': key} for key in self.operations]

    def validate(self, op, parameters, **kwargs):
        if set(parameters) - set(self.operations[op]['request_schema']['properties']):
            raise ForgeError('CONTRACT_UNKNOWN_FIELD')
        return copy.deepcopy(parameters)

    def quote(self, op, parameters, **kwargs):
        price = self.operations[op]['test_price']
        return {'credits': price, 'price_status': 'EXACT' if price is not None else 'UNKNOWN',
                'spend_allowed': price is not None, 'contract_version':'test1', 'authorization':'NOT_GRANTED_BY_CATALOGUE'}


class FakeCLI:
    executable = 'FAKE_ONLY_NO_SHELL'
    def __init__(self):
        self.creates = []; self.gets = []; self.tasks = {}; self.fail_post = False
        self.before_create = None; self.pages = {}; self.lock = threading.Lock()

    def auth(self): return {'authenticated':True,'verified':True}
    def balance(self): return {'balance':3079}

    @staticmethod
    def envelope(body, method):
        return {'schema_version':'v1','ok':True,'result':{'http_status':200,'method':method,'path':'/resource','api':'v1','body':body,'saved_json':None}}

    def request(self, contract, action, task_id=None, payload=None, query=None, timeout=None):
        if action == 'create':
            if self.before_create:
                self.before_create()
            with self.lock:
                task_id = '00000000-0000-0000-0000-' + str(len(self.creates)+1).zfill(12)
                self.creates.append((contract['id'], copy.deepcopy(payload)))
                self.tasks[task_id] = {'id':task_id,'name':payload.get('name'),'status':'IN_PROGRESS','progress':0,'consumed_credits':0}
            if self.fail_post:
                raise ForgeError('SIMULATED_LOST_REPLY')
            return self.envelope({'result':task_id}, 'POST')
        if action == 'get':
            self.gets.append((task_id,timeout))
            return self.envelope(copy.deepcopy(self.tasks[task_id]), 'GET')
        if action == 'list':
            return self.envelope(copy.deepcopy(self.pages.get((query or {}).get('page_num',1), {'result':[],'next_page_num':None})), 'GET')
        raise AssertionError('UNEXPECTED_ACTION')


class CapabilityEngineSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.refs = self.root/'refs'; self.refs.mkdir()
        self.source = self.refs/'source.png'; self.source.write_bytes(png((70,70,70)))
        self.cli = FakeCLI(); self.catalog = FakeCatalog()
        self.forge = Forge(self.root/'forge', self.cli, reference_roots=[self.refs],
                           spending_enabled=True, spending_job_ids={'AHU'}, max_credits=500)
        self.engine = CapabilityEngine(self.forge, self.catalog)

    def create(self, op='main', capability='image_to_3d.generate', parameters=None, **kwargs):
        return self.engine.create_operation('AHU', capability,
            parameters if parameters is not None else {'image_url':{'local_path':str(self.source)}}, operation_id=op, **kwargs)

    def succeeded(self, op='main', credits=5):
        result = self.engine.submit_operation('AHU',op); task_id=result['task_id']
        self.cli.tasks[task_id].update(status='SUCCEEDED',progress=100,consumed_credits=credits,
                                       image_urls=['https://assets.meshy.ai/preview.png'])
        self.engine.refresh_operation('AHU',op)
        return task_id

    def test_plan_uses_same_ledger_private_manifest_and_asset_lineage(self):
        result = self.create()
        self.assertEqual(result['status'],'PLANNED'); self.assertEqual(result['reservation'],0)
        self.assertEqual(self.forge.get_job('AHU')['job']['workflow_kind'],'capability')
        row = self.engine._row('AHU','main'); manifest = Path(row['manifest_path'])
        self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('data:image',manifest.read_text()); self.assertNotIn('https://',manifest.read_text())
        self.assertEqual(len(self.engine.registry.list()),1)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],0)
        self.assertEqual(self.cli.creates,[])

    def test_disabled_and_unknown_price_never_persist_paid_intent(self):
        self.create(); self.forge.spending_enabled=False
        with self.assertRaisesRegex(ForgeError,'SPENDING_DISABLED'):
            self.engine.submit_operation('AHU')
        self.forge.spending_enabled=True; self.create('unknown','unknown.create',{'prompt':'test'})
        with self.assertRaisesRegex(ForgeError,'EXACT_VERIFIED_PRICE'):
            self.engine.submit_operation('AHU','unknown')
        self.assertEqual(self.engine.get_operation('AHU','unknown')['status'],'PLANNED')
        self.assertEqual(self.cli.creates,[])

    def test_operator_zero_credit_ceiling_is_readonly_and_blocks_before_intent(self):
        self.create(); engine=CapabilityEngine(self.forge,self.catalog,max_operation_credits=0)
        with self.assertRaises(AttributeError):engine.max_operation_credits=500
        with self.assertRaisesRegex(ForgeError,'EXCEEDS_OPERATOR_CEILING'):
            engine.submit_operation('AHU')
        row=engine.get_operation('AHU')
        self.assertEqual(row['status'],'PLANNED');self.assertEqual(row['reservation'],0)
        self.assertIsNone(row['request_sha']);self.assertEqual(self.cli.creates,[])

    def test_operator_zero_credit_ceiling_permits_only_exact_free_fake_operation(self):
        self.catalog.operations['text_to_3d.preview']['test_price']=0
        engine=CapabilityEngine(self.forge,self.catalog,max_operation_credits=0)
        engine.create_operation('AHU','text_to_3d.preview',{'prompt':'free fake only'})
        result=engine.submit_operation('AHU')
        self.assertEqual(result['reservation'],0);self.assertEqual(result['status'],'PENDING')
        self.assertEqual(len(self.cli.creates),1)

    def test_final_named_payload_quote_must_remain_exact_before_intent(self):
        self.create()
        exact={'credits':5,'price_status':'EXACT','spend_allowed':True}
        stale={'credits':None,'price_status':'UNKNOWN','spend_allowed':False}
        with patch.object(self.catalog,'quote',side_effect=[exact,stale]):
            with self.assertRaisesRegex(ForgeError,'QUOTE_CHANGED'):
                self.engine.submit_operation('AHU')
        self.assertEqual(self.engine.get_operation('AHU')['status'],'PLANNED')
        self.assertEqual(self.cli.creates,[])

    def test_concurrent_submitters_create_once_and_share_reservation(self):
        self.create(); barrier=threading.Barrier(2)
        def submit():
            barrier.wait()
            try:self.engine.submit_operation('AHU');return 'sent'
            except ForgeError:return 'blocked'
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:submit(),range(2)))
        self.assertCountEqual(results,['sent','blocked']);self.assertEqual(len(self.cli.creates),1)
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],5)

    def test_unknown_survives_restart_and_does_not_repeat(self):
        self.create()
        def check_intent():
            result=self.engine.get_operation('AHU')
            self.assertEqual(result['status'],'SUBMISSION_UNKNOWN');self.assertEqual(result['reservation'],5)
            self.assertEqual(len(result['request_sha']),64)
        self.cli.before_create=check_intent;self.cli.fail_post=True
        with self.assertRaisesRegex(ForgeError,'SUBMISSION_UNKNOWN'):
            self.engine.submit_operation('AHU')
        restarted=CapabilityEngine(self.forge,self.catalog)
        with self.assertRaisesRegex(ForgeError,'ALREADY_SUBMITTED'):
            restarted.submit_operation('AHU')
        self.assertEqual(len(self.cli.creates),1)

    def test_budget_includes_existing_legacy_stage_and_pending_actual_zero(self):
        self.create()
        with self.forge._db() as c:
            c.execute('INSERT INTO stages(job_id,stage,status,task_id,reservation,actual,intent_at,updated) VALUES(?,?,?,?,?,?,?,?)',('AHU','prototype','SUCCEEDED','11111111-1111-1111-1111-111111111111',6,6,0,0))
        self.forge.max_credits=10
        with self.assertRaisesRegex(ForgeError,'BUDGET_EXCEEDED'):
            self.engine.submit_operation('AHU')
        self.assertEqual(self.cli.creates,[])
        self.forge.max_credits=500;self.engine.submit_operation('AHU');self.engine.refresh_operation('AHU')
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],11)

    def test_rejected_job_cannot_plan_generic_build_or_upload_another_reference(self):
        self.create()
        with self.forge._db() as c:c.execute('UPDATE jobs SET rejected=1 WHERE id="AHU"')
        with self.assertRaisesRegex(ForgeError,'REJECTED'):
            self.create('bypass','creative_lab.brick_figure.build',{'input_task_id':'11111111-1111-1111-1111-111111111111'})
        self.assertFalse((self.forge.root/'jobs/AHU/operations/bypass').exists())

    def test_internal_references_urls_and_secret_values_are_not_accepted(self):
        for value in [{'reference':{'local_copy':'/private'}},'https://attacker.invalid/secret','data:image/png;base64,PRIVATE']:
            with self.assertRaises(ForgeError):self.create(parameters={'image_url':value})
        with self.assertRaisesRegex(ForgeError,'SECRET'):
            self.create(parameters={'prompt':'Bearer synthetic-private-value'})
        self.assertEqual(self.cli.creates,[])

    def test_media_cardinality_and_byte_budget_reject_before_copy(self):
        op=self.catalog.operations['image_to_3d.generate']
        op['request_schema']['properties']['image_url']={'type':'array','maxItems':4}
        op['input_fields']['image_url']['many']=True
        with patch.object(self.engine,'_copy_reference',side_effect=AssertionError('MUST_NOT_COPY')) as copier:
            with self.assertRaisesRegex(ForgeError,'ARRAY_CONTRACT_BOUND'):
                self.create(parameters={'image_url':[{'local_path':str(self.source)}]*5})
            copier.assert_not_called()
        model=self.refs/'oversize.glb'
        with model.open('wb') as f:f.truncate(100_000_001)
        with patch.object(self.engine,'_copy_reference',side_effect=AssertionError('MUST_NOT_COPY')) as copier:
            with self.assertRaisesRegex(ForgeError,'BYTE_LIMIT'):
                self.create(parameters={'model_url':{'local_path':str(model)}})
            copier.assert_not_called()

    def test_parent_type_field_constraint_is_enforced_within_submit_gate(self):
        self.create('parent');self.succeeded('parent')
        contract=copy.deepcopy(self.catalog.operations['remesh.create'])
        contract['id']='animation.create';contract['input_fields']={'rig_task_id':{'kind':'task_id','allowed_parent_capabilities':['rigging.create']}}
        contract['request_schema']['properties']={'rig_task_id':{},'name':{}}
        self.catalog.operations['animation.create']=contract
        self.create('animate','animation.create',{'rig_task_id':{'task_from_operation':'parent'}})
        with self.assertRaisesRegex(ForgeError,'FIELD_PRODUCT_MISMATCH'):
            self.engine.submit_operation('AHU','animate')
        self.assertEqual(len(self.cli.creates),1)

    def test_dependency_and_same_job_parent_required_before_child_post(self):
        self.create('parent')
        self.create('child','remesh.create',{'input_task_id':{'task_from_operation':'parent'}})
        with self.assertRaisesRegex(ForgeError,'DEPENDENCY_NOT_SUCCEEDED'):
            self.engine.submit_operation('AHU','child')
        parent=self.succeeded('parent')
        child=self.engine.submit_operation('AHU','child')
        self.assertEqual(self.cli.creates[-1][1]['input_task_id'],parent)
        self.assertEqual(child['status'],'PENDING')
        self.create('foreign','remesh.create',{'input_task_id':'99999999-9999-9999-9999-999999999999'})
        with self.assertRaisesRegex(ForgeError,'SAME_JOB'):
            self.engine.submit_operation('AHU','foreign')

    def test_parent_visual_gate_rejects_succeeded_and_wrong_product(self):
        self.create('parent');self.succeeded('parent')
        self.create('wrong','creative_lab.brick_figure.build',{'input_task_id':{'task_from_operation':'parent'}})
        with self.assertRaisesRegex(ForgeError,'PARENT_PRODUCT'):
            self.engine.submit_operation('AHU','wrong')
        self.create('proto','creative_lab.brick_figure.prototype');self.succeeded('proto',6)
        self.create('build','creative_lab.brick_figure.build',{'input_task_id':{'task_from_operation':'proto'}})
        with self.assertRaisesRegex(ForgeError,'VISUAL_APPROVAL_REQUIRED'):
            self.engine.submit_operation('AHU','build')
        self.assertEqual(len(self.cli.creates),2)

    def test_expired_vendor_parent_blocks_before_child_intent(self):
        self.create('parent');parent=self.succeeded('parent')
        self.cli.tasks[parent]['expires_at']=1
        self.create('child','remesh.create',{'input_task_id':{'task_from_operation':'parent'}})
        with self.assertRaisesRegex(ForgeError,'ASSETS_EXPIRED'):
            self.engine.submit_operation('AHU','child')
        self.assertEqual(len(self.cli.creates),1)
        self.assertEqual(self.engine.get_operation('AHU','child')['status'],'PLANNED')

    def test_official_rigging_animation_named_variants_are_exact_and_url_private(self):
        task={'result':{'rigged_character_glb_url':'https://assets.meshy.ai/rig.glb',
                        'basic_animations':{'walking_armature_glb_url':'https://assets.meshy.ai/walk.glb'},
                        'processed_animation_fps_fbx_url':'https://assets.meshy.ai/fps.fbx'}}
        self.assertEqual(self.engine._asset_url(task,'glb'),'https://assets.meshy.ai/rig.glb')
        self.assertEqual(self.engine._asset_url(task,'glb',variant='walking_armature_glb'),'https://assets.meshy.ai/walk.glb')
        self.assertEqual(self.engine._asset_url(task,'fbx',variant='processed_animation_fps_fbx'),'https://assets.meshy.ai/fps.fbx')
        with self.assertRaisesRegex(ForgeError,'VARIANT_OR_FORMAT'):
            self.engine._asset_url(task,'glb',variant='processed_animation_fps_fbx')
        with self.assertRaisesRegex(ForgeError,'VARIANT_OR_FORMAT'):
            self.engine._asset_url(task,'glb',variant='arbitrary_private_field')

    def test_preview_approval_requires_same_download_receipt_and_rechecks_hash(self):
        self.create('proto','creative_lab.brick_figure.prototype');self.succeeded('proto',6)
        class Response(io.BytesIO):
            def geturl(self):return 'https://assets.meshy.ai/preview.png'
        class Opener:
            def open(self,*args,**kwargs):return Response(png((1,2,3)))
        with patch('kai_meshy.capability_engine.build_opener',return_value=Opener()):
            asset=self.engine.download_operation('AHU','proto','image')
        self.engine.approve_operation('AHU','proto',asset['asset_id'],'owner')
        self.create('build','creative_lab.brick_figure.build',{'input_task_id':{'task_from_operation':'proto'}})
        Path(asset['path']).write_bytes(b'tampered')
        with self.assertRaisesRegex(ForgeError,'ASSET_CHANGED'):
            self.engine.submit_operation('AHU','build')
        self.assertEqual(len(self.cli.creates),1)

    def test_content_dedup_keeps_input_role_and_still_binds_exact_output_approval(self):
        self.create('proto','creative_lab.brick_figure.prototype');self.succeeded('proto',6)
        class Response(io.BytesIO):
            def geturl(self):return 'https://assets.meshy.ai/preview.png'
        class Opener:
            def open(self,*args,**kwargs):return Response(self_source)
        self_source=self.source.read_bytes()
        with patch('kai_meshy.capability_engine.build_opener',return_value=Opener()):
            asset=self.engine.download_operation('AHU','proto','image')
        self.assertEqual(self.engine.registry.get(asset['asset_id'])['role'],'reference')
        self.engine.approve_operation('AHU','proto',asset['asset_id'],'owner')
        self.create('build','creative_lab.brick_figure.build',{'input_task_id':{'task_from_operation':'proto'}})
        Path(asset['path']).write_bytes(png((9,9,9)))
        with self.assertRaisesRegex(ForgeError,'PREVIEW_CHANGED'):
            self.engine.submit_operation('AHU','build')
        self.assertEqual(len(self.cli.creates),1)

    def test_real_catalogue_print_glb_plan_is_exact_zero_without_submission(self):
        from kai_meshy.contracts import CapabilityCatalog
        metadata=json.dumps({'asset':{'version':'2.0'},'meshes':[{}]}).encode()
        metadata+=b' '*(-len(metadata)%4)
        raw=struct.pack('<4sII',b'glTF',2,20+len(metadata))+struct.pack('<II',len(metadata),0x4e4f534a)+metadata
        model=self.refs/'source.glb';model.write_bytes(raw)
        engine=CapabilityEngine(self.forge,CapabilityCatalog(),max_operation_credits=0)
        result=engine.create_operation('AHU','print.analyze',{'model_url':{'local_path':str(model)}})
        self.assertEqual(result['quote']['price_status'],'EXACT');self.assertEqual(result['quote']['credits'],0)
        self.assertEqual(result['status'],'PLANNED');self.assertEqual(self.cli.creates,[])
        row=engine._row('AHU','main');manifest=engine._read_manifest(row)
        wire=engine._wire('AHU',manifest['parameters'],engine.describe('print.analyze'),ready=False)
        self.assertTrue(wire['model_url'].startswith('data:model/gltf-binary;base64,'))
        bad=self.refs/'source.stl';bad.write_bytes(b'solid mesh\nendsolid mesh\n')
        with self.assertRaisesRegex(ForgeError,'INLINE_MIME_NOT_SUPPORTED'):
            engine.create_operation('AHU','print.analyze',{'model_url':{'local_path':str(bad)}},operation_id='bad_stl')
        self.assertEqual(self.cli.creates,[])

    def test_reference_mutation_before_intent_blocks_upload(self):
        self.create();row=self.engine._row('AHU','main');manifest=json.loads(Path(row['manifest_path']).read_text())
        Path(manifest['parameters']['image_url']['reference']['local_copy']).write_bytes(b'changed')
        with self.assertRaises(ForgeError):self.engine.submit_operation('AHU')
        self.assertEqual(self.engine.get_operation('AHU')['status'],'PLANNED');self.assertEqual(self.cli.creates,[])

    def test_remote_identity_refresh_and_pure_get_are_strict(self):
        self.create();task_id=self.succeeded()
        before=self.forge.get_job('AHU')
        result=self.engine.get_remote('image_to_3d.generate',task_id,timeout=.5)
        self.assertEqual(result['id'],task_id);self.assertNotIn('image_urls',result)
        self.assertEqual(self.forge.get_job('AHU'),before)
        self.cli.tasks[task_id]['id']='99999999-9999-9999-9999-999999999999'
        with self.assertRaisesRegex(ForgeError,'ID_OR_STATE_MISMATCH'):self.engine.refresh_operation('AHU')

    def test_poll_timeout_is_passed_as_remaining_and_stall_limit_stops(self):
        self.create();self.engine.submit_operation('AHU')
        with patch('kai_meshy.capability_engine.time.sleep'):
            result=self.engine.poll_operation('AHU',timeout=.5,interval=.05,max_stalled=2)
        self.assertEqual(result['wait_stop'],'NO_PROGRESS_RECONCILE_SAME_TASK')
        self.assertTrue(all(timeout<=.5 for _,timeout in self.cli.gets))
        self.assertEqual(len(self.cli.creates),1)

    def test_unknown_reconciliation_requires_original_fingerprint_and_name(self):
        self.create();self.cli.fail_post=True
        with self.assertRaises(ForgeError):self.engine.submit_operation('AHU')
        row=self.engine.get_operation('AHU');task_id=next(iter(self.cli.tasks))
        with self.assertRaisesRegex(ForgeError,'IDENTITY_MISMATCH'):
            self.engine.reconcile_operation('AHU','main',task_id,'wrong')
        self.cli.tasks[task_id].update(status='SUCCEEDED',consumed_credits=5)
        result=self.engine.reconcile_operation('AHU','main',task_id,row['request_sha'])
        self.assertEqual(result['status'],'SUCCEEDED');self.assertEqual(len(self.cli.creates),1)

    def test_listing_follows_pages_and_stops_repeated_cursor_without_private_urls(self):
        task={'id':'00000000-0000-0000-0000-000000000001','status':'SUCCEEDED','image_urls':['https://assets.meshy.ai/private']}
        self.cli.pages={1:{'result':[task],'next_page_num':2},2:{'result':[task],'next_page_num':2}}
        result=self.engine.list_history('image_to_3d.generate',max_pages=5)
        self.assertEqual(result['stop'],'REPEATED_CURSOR');self.assertEqual(len(result['pages']),2)
        self.assertNotIn('https://',json.dumps(result));self.assertEqual(self.cli.creates,[])

    def test_numbered_bare_array_pagination_requires_observed_empty_page(self):
        task={'id':'00000000-0000-0000-0000-000000000001','status':'SUCCEEDED'}
        self.cli.pages={1:[task],2:[task],3:[]}
        result=self.engine.list_history('image_to_3d.generate',max_pages=5,page_size=50)
        self.assertEqual(len(result['pages']),3);self.assertTrue(result['exhausted_available_pages'])
        self.assertFalse(result['complete_history'])

    def test_local_cancel_preserves_remote_and_blocks_new_steps(self):
        self.create();self.engine.submit_operation('AHU');self.engine.cancel_local('AHU')
        self.assertEqual(self.forge.budget_status()['committed_or_actual_credits'],5)
        self.assertEqual(self.engine.poll_operation('AHU')['wait_stop'],'LOCAL_CANCEL_REMOTE_UNCHANGED')
        with self.assertRaisesRegex(ForgeError,'REJECTED'):self.create('new')

    def test_archive_traversal_rejected_and_code_never_extracted(self):
        unsafe=self.root/'bad.zip'
        with zipfile.ZipFile(unsafe,'w') as archive:archive.writestr('../private.txt','private')
        with self.assertRaisesRegex(ForgeError,'UNSAFE_MEMBER'):self.engine._audit_zip(unsafe)
        self.create();self.succeeded()
        row=self.engine._row('AHU','main');folder=Path(row['manifest_path']).parent/'outputs';folder.mkdir()
        safe=folder/'models.obj.zip'
        with zipfile.ZipFile(safe,'w') as archive:
            archive.writestr('model.obj','v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n');archive.writestr('run.py','raise RuntimeError("NEVER_EXECUTE")')
        asset=self.engine.registry.register(safe,'model')
        result=self.engine.extract_operation_archive('AHU','main',asset['id'])
        self.assertFalse(result['executed_code']);self.assertEqual(len(result['files']),1)
        self.assertFalse(any(p.name=='run.py' for p in folder.rglob('*')))


class InternalCatalogueRESTAdapter(unittest.TestCase):
    def test_standard_v2_creative_routes_and_timeouts_are_bound_to_contract(self):
        cli=MeshyCLI('NO_EXECUTION');catalog=FakeCatalog()
        for op,flag,path in [('image_to_3d.generate','--v1','/resource'),('text_to_3d.preview','--v2','/resource'),('creative_lab.brick_figure.prototype','--creative-lab','/resource')]:
            with patch.object(cli,'run',return_value={'ok':True}) as run:
                cli.request(catalog.describe(op),'get',task_id='11111111-1111-1111-1111-111111111111',timeout=.5)
            args=run.call_args.args;self.assertIn(flag,args);self.assertEqual(args[2],path+'/11111111-1111-1111-1111-111111111111')
            self.assertEqual(run.call_args.kwargs['timeout'],.5)
        bad=catalog.describe('image_to_3d.generate');bad['routes']['create']='https://attacker.invalid/post'
        with self.assertRaisesRegex(ForgeError,'ROUTE_INVALID'):cli.request(bad,'create',payload={})
        with self.assertRaisesRegex(ForgeError,'PAYLOAD_NOT_ALLOWED'):
            cli.request(catalog.describe('image_to_3d.generate'),'get',task_id='11111111-1111-1111-1111-111111111111',payload={})


if __name__=='__main__':unittest.main()
