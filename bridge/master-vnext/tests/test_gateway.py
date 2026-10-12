import io
import json
import os
import pathlib
import shutil
import tempfile
import threading
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

from kai_master_bridge.contracts import Action, InvalidRequest, SCHEMA
from kai_master_bridge.gateway import Gateway
from kai_master_bridge.ledger import LedgerError
from kai_master_bridge.mcp_stdio import MCP, serve

class GatewayCases(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.safe=self.root/'allowed';self.safe.mkdir()
        (self.safe/'canary.txt').write_text('hello master',encoding='utf-8')
        self.outside=self.root/'outside.txt';self.outside.write_text('outside',encoding='utf-8')
        self.config=self.root/'config.json'
        self.caps={x:{'enabled':x in ('host.status','fs.list','fs.sha256')}
                  for x in ('host.status','fs.list','fs.sha256','pc.agent.health','pc.agent.apps',
                            'pc.agent.launch','android.adb.devices','android.adb.model',
                            'android.adb.launch','pc.gui.windows')}
        self.settings={'node_id':'unit-test','roots':{'data':str(self.safe)},
                       'capabilities':self.caps,
                       'pc_agent':{'port':18761,'allowed_app_ids':['notepad']},
                       'android':{'allowed_packages':['com.example.app']}}
        self.set_config()
        self.gw=Gateway(self.config,self.root/'state')

    def set_config(self):
        self.config.write_text(json.dumps(self.settings),encoding='utf-8')

    def action(self,cap='host.status',params=None,request_id=None,deadline=None,node='unit-test'):
        return {'schema':SCHEMA,'request_id':request_id or str(uuid.uuid4()),'node_id':node,
                'capability':cap,'params':{} if params is None else params,
                'deadline':int(time.time())+120 if deadline is None else deadline}

    def test_01_status(self):
        x=self.gw.status();self.assertFalse(x['remote_listener']);self.assertIn('host.status',x['capabilities'])
    def test_02_local_host(self):
        self.assertEqual(self.gw.execute(self.action())['status'],'COMPLETED')
    def test_03_action_repeat_receipt(self):
        a=self.action();self.assertEqual(self.gw.execute(a),self.gw.execute(a))
    def test_04_conflicting_same_id(self):
        a=self.action();self.gw.execute(a);b=dict(a);b['params']={'more':1}
        self.assertEqual(self.gw.execute(b)['error'],'REQUEST_ID_CONFLICT')
    def test_05_stale(self):
        self.assertEqual(self.gw.execute(self.action(deadline=int(time.time())-1))['status'],'DENIED')
    def test_06_far_future(self):
        self.assertEqual(self.gw.execute(self.action(deadline=int(time.time())+500))['status'],'DENIED')
    def test_07_wrong_node(self):
        self.assertEqual(self.gw.execute(self.action(node='impostor'))['error'],'UNKNOWN_NODE')
    def test_08_unknown_capability(self):
        self.assertEqual(self.gw.execute(self.action(cap='powershell.run'))['status'],'DENIED')
    def test_09_disabled_gui(self):
        self.assertEqual(self.gw.execute(self.action(cap='pc.gui.windows'))['status'],'DENIED')
    def test_10_safe_list(self):
        r=self.gw.execute(self.action('fs.list',{'root':'data','relative':'canary.txt'}))
        self.assertEqual(r['status'],'FAILED')
        r=self.gw.execute(self.action('fs.list',{'root':'data','relative':'sub'}))
        self.assertEqual(r['status'],'FAILED')
        (self.safe/'sub').mkdir()
        self.assertEqual(self.gw.execute(self.action('fs.list',{'root':'data','relative':'sub'}))['status'],'COMPLETED')
    def test_11_hash(self):
        import hashlib
        r=self.gw.execute(self.action('fs.sha256',{'root':'data','relative':'canary.txt'}))
        self.assertEqual(r['result']['sha256'],hashlib.sha256(b'hello master').hexdigest())
    def test_12_parent_escape(self):
        r=self.gw.execute(self.action('fs.sha256',{'root':'data','relative':'../outside.txt'}))
        self.assertEqual(r['status'],'FAILED')
    def test_13_absolute_escape(self):
        r=self.gw.execute(self.action('fs.sha256',{'root':'data','relative':str(self.outside)}))
        self.assertEqual(r['status'],'FAILED')
    def test_14_secret_name(self):
        (self.safe/'secret-token.txt').write_text('not a secret',encoding='utf-8')
        r=self.gw.execute(self.action('fs.sha256',{'root':'data','relative':'secret-token.txt'}))
        self.assertEqual(r['status'],'FAILED')
    def test_15_symlink_escape(self):
        try:(self.safe/'link.txt').symlink_to(self.outside)
        except (OSError,NotImplementedError):self.skipTest('No symlinks on platform')
        self.assertEqual(self.gw.execute(self.action('fs.sha256',{'root':'data','relative':'link.txt'}))['status'],'FAILED')
    def test_16_root_escape(self):
        self.assertEqual(self.gw.execute(self.action('fs.sha256',{'root':'unknown','relative':'x'}))['status'],'FAILED')
    def test_17_reject_missing_params(self):
        self.assertEqual(self.gw.execute(self.action('fs.sha256',{'root':'data'}))['status'],'FAILED')
    def test_18_bad_request_uuid(self):
        a=self.action();a['request_id']='not-a-uuid'
        self.assertEqual(self.gw.execute(a)['status'],'DENIED')
    def test_19_bad_extra_field(self):
        a=self.action();a['admin']=True
        self.assertEqual(self.gw.execute(a)['status'],'DENIED')
    def test_20_giant_params(self):
        a=self.action();a['params']={'input':'x'*(33*1024)}
        self.assertEqual(self.gw.execute(a)['status'],'DENIED')
    def test_21_default_deny_act(self):
        self.assertEqual(self.gw.execute(self.action('pc.agent.launch',{'app_id':'notepad'}))['status'],'DENIED')
    def test_22_pending_local_approval(self):
        self.caps['pc.agent.launch']['enabled']=True;self.set_config()
        fresh=Gateway(self.config,self.root/'state');a=self.action('pc.agent.launch',{'app_id':'notepad'})
        r=fresh.execute(a)
        self.assertEqual(r['status'],'PENDING_LOCAL_APPROVAL')
        self.assertEqual(r['result']['approve_digest'],Action.parse(a).digest())
    def test_23_approval_forged_digest_fails(self):
        self.caps['pc.agent.launch']['enabled']=True;self.set_config()
        fresh=Gateway(self.config,self.root/'state');a=self.action('pc.agent.launch',{'app_id':'notepad'})
        fresh.ledger.add_approval(a['request_id'],'0'*64)
        self.assertEqual(fresh.execute(a)['status'],'PENDING_LOCAL_APPROVAL')
    def test_24_approval_unavailable_adapter_still_bounded(self):
        self.caps['pc.agent.launch']['enabled']=True;self.set_config()
        fresh=Gateway(self.config,self.root/'state');a=self.action('pc.agent.launch',{'app_id':'notepad'})
        fresh.ledger.add_approval(a['request_id'],Action.parse(a).digest())
        r=fresh.execute(a)
        self.assertEqual(r['status'],'FAILED')
        self.assertEqual(r['error'],'ADAPTER_REJECTED_OR_UNAVAILABLE')
    def test_25_approval_different_args_denied(self):
        self.caps['pc.agent.launch']['enabled']=True;self.set_config()
        fresh=Gateway(self.config,self.root/'state');a=self.action('pc.agent.launch',{'app_id':'notepad'})
        fresh.ledger.add_approval(a['request_id'],Action.parse(a).digest())
        b=dict(a);b['params']={'app_id':'cmd'}
        self.assertEqual(fresh.execute(b)['status'],'PENDING_LOCAL_APPROVAL')
    def test_26_stop_kills_actions(self):
        self.gw.stop_flag.write_text('stop',encoding='utf-8')
        self.assertEqual(self.gw.execute(self.action('fs.list',{'root':'data','relative':'sub'}))['error'],
                         'GLOBAL_KILL_SWITCH_ACTIVE')
        self.assertEqual(self.gw.execute(self.action('host.status'))['status'],'COMPLETED')
    def test_27_mcp_initialize(self):
        m=MCP(self.gw)
        r=m.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})
        self.assertEqual(r['result']['serverInfo']['name'],'kai-master-bridge-lab')
    def test_28_mcp_tools(self):
        m=MCP(self.gw)
        self.assertEqual(len(m.handle({'jsonrpc':'2.0','id':2,'method':'tools/list'})['result']['tools']),2)
    def test_29_mcp_call_status(self):
        m=MCP(self.gw)
        r=m.handle({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{
           'name':'kai_master_status','arguments':{}}})
        self.assertFalse(r['result']['isError'])
    def test_30_mcp_bad_args(self):
        m=MCP(self.gw)
        r=m.handle({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{
           'name':'kai_master_status','arguments':{'execute':'something'}}})
        self.assertEqual(r['error']['message'],'UNKNOWN_TOOL_OR_ARGUMENTS')
    def test_31_notification_no_answer(self):
        self.assertIsNone(MCP(self.gw).handle({'jsonrpc':'2.0','method':'notifications/initialized'}))
    def test_32_mcp_end_to_end(self):
        a=self.action();data=io.StringIO(json.dumps({'jsonrpc':'2.0','id':6,'method':'tools/call','params':{
          'name':'kai_master_action','arguments':{'action':a}}})+'\n');out=io.StringIO()
        serve(self.config,self.root/'state',stdin=data,stdout=out)
        self.assertIn('COMPLETED',out.getvalue())
    def test_33_parallel_same_idempotent(self):
        a=self.action('fs.sha256',{'root':'data','relative':'canary.txt'})
        with ThreadPoolExecutor(max_workers=12) as pool:
            r=list(pool.map(lambda _ : self.gw.execute(a),range(24)))
        self.assertTrue(all(x.get('status') in ('COMPLETED','IN_PROGRESS_OR_INTERRUPTED') for x in r))
        with self.gw.ledger.open() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM actions WHERE request_id=?',(a['request_id'],)).fetchone()[0],1)
    def test_34_no_secret_params_in_ledger(self):
        a=self.action('fs.list',{'root':'data','relative':'PASSWORD_ABC'})
        self.gw.execute(a)
        blob=(self.root/'state'/'master.sqlite3').read_bytes()
        self.assertNotIn(b'PASSWORD_ABC',blob)
    def test_35_reject_bad_policy_key(self):
        from kai_master_bridge.policy import Policy,PolicyError
        self.caps['powershell.run']={'enabled':True};self.set_config()
        with self.assertRaises(PolicyError):Gateway(self.config,self.root/'state')
    def test_36_approval_is_not_mcp_method(self):
        m=MCP(self.gw)
        x=m.handle({'jsonrpc':'2.0','id':7,'method':'tools/call','params':{
          'name':'approve','arguments':{}}})
        self.assertIn('error',x)

if __name__=='__main__':unittest.main()
