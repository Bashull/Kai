import http.client
import json
import pathlib
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from kai_pc_agent import handler_factory

class SecurityContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = {"apps": {"off": {"enabled": False, "path": "/tmp/not-real.exe"}}}
        self.server = ThreadingHTTPServer(("127.0.0.1",0), handler_factory(cfg,"test-token-of-sufficient-length-123456789",pathlib.Path(self.tmp.name)/"audit.jsonl"))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,method,path,body=None,authorized=True):
        c=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=2)
        headers={"Authorization":"Bearer test-token-of-sufficient-length-123456789"} if authorized else {}
        if body is not None: headers["Content-Type"]="application/json"
        c.request(method,path,body=body,headers=headers);r=c.getresponse();v=json.loads(r.read());s=r.status;c.close();return s,v
    def test_unauthenticated_denied(self): self.assertEqual(self.request("GET","/v1/health",authorized=False)[0],401)
    def test_health(self): self.assertEqual(self.request("GET","/v1/health")[0],200)
    def test_unknown_route(self): self.assertEqual(self.request("GET","/admin")[0],404)
    def test_unallowlisted_denied(self): self.assertEqual(self.request("POST","/v1/apps/launch",b'{"id":"cmd"}')[0],403)
    def test_extra_parameters_denied(self): self.assertEqual(self.request("POST","/v1/apps/launch",b'{"id":"off","args":["/c","dir"]}')[0],400)
    def test_malformed_json_denied(self): self.assertEqual(self.request("POST","/v1/apps/launch",b"{")[0],400)
    def test_large_body_denied(self): self.assertEqual(self.request("POST","/v1/apps/launch",b"x"*4100)[0],413)
    def test_list_apps_disabled_not_exposed(self): self.assertEqual(self.request("GET","/v1/apps")[1]["allowed_apps"],[])
if __name__=="__main__": unittest.main()
