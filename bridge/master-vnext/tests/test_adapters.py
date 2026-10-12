"""Isolation contract tests; mocks never operate on user devices."""
import http.server
import json
import pathlib
import tempfile
import threading
import time
import unittest
import uuid
from unittest import mock
from kai_master_bridge.adapters import Adapters,AdapterError
from kai_master_bridge.gateway import Gateway
from kai_master_bridge.contracts import SCHEMA,Action

class MockPc(http.server.BaseHTTPRequestHandler):
    received=[]
    def log_message(self,*args):pass
    def do_GET(self):
        if self.headers.get('Authorization')!='Bearer '+'x'*40:return self.send(401,{})
        if self.path=='/v1/health':return self.send(200,{'ok':True,'version':'0.1'})
        if self.path=='/v1/apps':return self.send(200,{'allowed_apps':['notepad']})
        return self.send(404,{})
    def do_POST(self):
        if self.headers.get('Authorization')!='Bearer '+'x'*40:return self.send(401,{})
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.received.append((self.path,data))
        if data=={'id':'notepad'}:return self.send(202,{'accepted':True})
        return self.send(403,{'error':'not_allowed'})
    def send(self,status,body):
        raw=json.dumps(body).encode()
        self.send_response(status);self.send_header('Content-Length',str(len(raw)))
        self.end_headers();self.wfile.write(raw)

class AdapterCases(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name)
        self.token=self.root/'token';self.token.write_text('x'*40)
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),MockPc)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.cfg={'node_id':'unit','roots':{'fixture':str(self.root)},
          'pc_agent':{'token_file':str(self.token),'port':self.server.server_port,
                      'allowed_app_ids':['notepad']},
          'android':{'adb_executable':'/does/not/exist','serial':'test-serial',
                     'allowed_packages':['com.example.app']},
          'capabilities':{x:{'enabled':True} for x in (
              'host.status','pc.agent.health','pc.agent.apps','pc.agent.launch',
              'android.adb.devices','android.adb.model','android.adb.launch','pc.gui.windows')}}
        self.adapters=Adapters(self.cfg)

    def test_pc_agent_health(self):
        self.assertEqual(self.adapters.execute('pc.agent.health',{})['response']['version'],'0.1')
    def test_pc_agent_list_apps(self):
        self.assertEqual(self.adapters.execute('pc.agent.apps',{})['response']['allowed_apps'],['notepad'])
    def test_pc_agent_launch_allowlisted(self):
        self.assertTrue(self.adapters.execute('pc.agent.launch',{'app_id':'notepad'})['response']['accepted'])
    def test_pc_agent_reject_nonallowlist(self):
        with self.assertRaises(AdapterError):self.adapters.execute('pc.agent.launch',{'app_id':'cmd'})
    def test_pc_agent_extra_arguments_rejected(self):
        with self.assertRaises(AdapterError):self.adapters.execute('pc.agent.launch',{'app_id':'notepad','argv':'/C'})
    def test_pc_agent_token_missing(self):
        self.cfg['pc_agent']['token_file']=str(self.root/'missing')
        with self.assertRaises(AdapterError):self.adapters.execute('pc.agent.health',{})
    def test_pc_agent_unprovisioned(self):
        self.cfg['pc_agent'].pop('token_file')
        with self.assertRaises(AdapterError):self.adapters.execute('pc.agent.health',{})
    def test_pc_agent_reject_token_bad(self):
        self.token.write_text('bad')
        with self.assertRaises(AdapterError):self.adapters.execute('pc.agent.health',{})
    def test_android_no_adb(self):
        with self.assertRaises(AdapterError):self.adapters.execute('android.adb.devices',{})
    def test_android_launch_not_approved(self):
        with self.assertRaises(AdapterError):self.adapters.execute('android.adb.launch',{'package':'com.example.bad'})
    def test_android_bad_package(self):
        with self.assertRaises(AdapterError):self.adapters.execute('android.adb.launch',{'package':'com.example.app;rm'})
    def test_adb_device_list_mock(self):
        self.cfg['android']['adb_executable']=str(self.root/'fake-adb.exe')
        with mock.patch('pathlib.Path.is_file',return_value=True),mock.patch('subprocess.run') as run:
            run.return_value=mock.Mock(returncode=0,stdout=b'List of devices attached\n123\tdevice product:a\n456\tunauthorized\n')
            result=self.adapters.execute('android.adb.devices',{})
            self.assertEqual(result['authorized_devices'],1)
            self.assertNotIn('123',str(result))
    def test_adb_launch_typed_argv_mock(self):
        self.cfg['android']['adb_executable']=str(self.root/'fake-adb.exe')
        with mock.patch('pathlib.Path.is_file',return_value=True),mock.patch('subprocess.run') as run:
            run.return_value=mock.Mock(returncode=0,stdout=b'Events injected: 1')
            result=self.adapters.execute('android.adb.launch',{'package':'com.example.app'})
            self.assertFalse(result['effect_observed'])
            self.assertEqual(run.call_args.args[0],[str(self.root/'fake-adb.exe'),'-s','test-serial','shell','monkey','-p','com.example.app','1'])
            self.assertFalse(run.call_args.kwargs.get('shell',False))
    def test_approval_e2e_mock_pc(self):
        cfg=self.root/'policy.json';cfg.write_text(json.dumps(self.cfg))
        gw=Gateway(cfg,self.root/'store')
        a={'schema':SCHEMA,'request_id':str(uuid.uuid4()),'node_id':'unit',
           'capability':'pc.agent.launch','params':{'app_id':'notepad'},'deadline':int(time.time())+120}
        self.assertEqual(gw.execute(a)['status'],'PENDING_LOCAL_APPROVAL')
        gw.ledger.add_approval(a['request_id'],Action.parse(a).digest())
        self.assertEqual(gw.execute(a)['status'],'COMPLETED')
        self.assertEqual(gw.execute(a)['status'],'COMPLETED')
        with gw.ledger.open() as db:
            self.assertEqual(db.execute('SELECT used FROM approvals WHERE request_id=?',(a['request_id'],)).fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM actions WHERE request_id=?',(a['request_id'],)).fetchone()[0],1)
    def test_no_approval_e2e_no_launch(self):
        cfg=self.root/'policy.json';cfg.write_text(json.dumps(self.cfg))
        MockPc.received=[]
        gw=Gateway(cfg,self.root/'store')
        a={'schema':SCHEMA,'request_id':str(uuid.uuid4()),'node_id':'unit',
           'capability':'pc.agent.launch','params':{'app_id':'notepad'},'deadline':int(time.time())+120}
        self.assertEqual(gw.execute(a)['status'],'PENDING_LOCAL_APPROVAL')
        self.assertEqual(MockPc.received,[])

if __name__=='__main__':unittest.main()
