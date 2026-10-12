"""Offline, no-socket tests for the dedicated phone-to-PC Master client."""
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from kai_master_bridge.ssh_client import ClientError, load_config, make_action, send


class SSHClientTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        key = self.root / "client-ed25519"
        known = self.root / "known_hosts"
        key.write_text("dummy-key-never-used")
        known.write_text("dummy-pinned-host")
        if os.name != "nt":
            key.chmod(0o600)
        self.config = {
            "node_id":"kai-pc-asier",
            "ssh_host":"192.168.1.12",
            "ssh_user":"ASIER",
            "ssh_port":22,
            "identity_file":str(key),
            "known_hosts":str(known),
            "allowed_apps":["notepad"],
        }
        self.path = self.root / "config.json"
        self.write_config()

    def write_config(self):
        self.path.write_text(json.dumps(self.config),encoding="utf-8")

    def action(self):
        return make_action(load_config(self.path),"host.status",{})

    def response(self, action, *, rid=None, status="COMPLETED", include_id=True):
        rec={"schema":"kai.master.receipt/1","status":status,"result":{}}
        if include_id:
            rec["request_id"]=action["request_id"] if rid is None else rid
        rpc={"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":json.dumps(rec)}]}}
        return subprocess.CompletedProcess(["ssh"],0,json.dumps(rpc)+"\n","")

    def test_lan_config_and_permissions(self):
        self.assertEqual(load_config(self.path)["ssh_host"],"192.168.1.12")

    def test_reject_public_host(self):
        self.config["ssh_host"]="8.8.8.8"
        self.write_config()
        with self.assertRaises(ClientError):
            load_config(self.path)

    def test_reject_invalid_user(self):
        self.config["ssh_user"]="-oProxyCommand=evil"
        self.write_config()
        with self.assertRaises(ClientError):
            load_config(self.path)

    @unittest.skipIf(os.name=="nt","Windows does not use Unix chmod for SSH keys")
    def test_reject_open_private_key(self):
        pathlib.Path(self.config["identity_file"]).chmod(0o644)
        with self.assertRaises(ClientError):
            load_config(self.path)

    def test_pinned_transport_never_builds_remote_shell(self):
        a=self.action()
        called=[]
        def fake(argv,**kwargs):
            called.append((argv,kwargs))
            return self.response(a)
        rec=send(load_config(self.path),a,runner=fake)
        self.assertEqual(rec["status"],"COMPLETED")
        argv,kw=called[0]
        self.assertEqual(argv[-1],"ASIER@192.168.1.12")
        self.assertIn("StrictHostKeyChecking=yes",argv)
        self.assertIn("BatchMode=yes",argv)
        self.assertEqual(argv[:3],["ssh","-F","/dev/null"])
        self.assertFalse(kw["shell"])
        parsed=json.loads(kw["input"])
        self.assertEqual(parsed["params"]["arguments"]["action"],a)

    def test_policy_denial_without_request_id(self):
        a=self.action()
        out=send(load_config(self.path),a,
                 runner=lambda *args,**kwargs:self.response(a,status="DENIED",include_id=False))
        self.assertEqual(out["status"],"DENIED")

    def test_reject_mismatched_receipt(self):
        a=self.action()
        with self.assertRaises(ClientError):
            send(load_config(self.path),a,
                 runner=lambda *args,**kwargs:self.response(a,rid="wrong"))

    def test_reject_remote_execution_failure(self):
        a=self.action()
        def failed(cmd,**kwargs):
            return subprocess.CompletedProcess(cmd,126,"","refused")
        with self.assertRaises(ClientError):
            send(load_config(self.path),a,runner=failed)


if __name__=="__main__":
    unittest.main()
