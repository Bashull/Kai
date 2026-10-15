"""Bounded source package exceptions do not authorize other packages or secrets."""
import contextlib,io,json,pathlib,tempfile,unittest,zipfile
from unittest import mock
import capture_resources as c


class ResourceTests(unittest.TestCase):
    def test_explicit_package_scope_and_secret_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);package=root/'node_modules'/'allowed';package.mkdir(parents=True)
            good=package/'index.js';good.write_text('export const fixture = 1;\n')
            other=root/'node_modules'/'other'/'index.js';other.parent.mkdir();other.write_text('other package')
            secret=package/'token.txt';secret.write_text('gh'+'p_'+'A'*36)
            req=root/'request.json';req.write_text(json.dumps({'files':[str(good),str(other),str(secret)],'explicit_package_roots':[str(package)]}))
            out=root/'out'
            with mock.patch('sys.argv',['capture_resources','--request',str(req),'--output',str(out)]),contextlib.redirect_stdout(io.StringIO()):c.main()
            rows=json.loads((out/'RESOURCE_MANIFEST.json').read_text())['rows']
            self.assertEqual([r['state'] for r in rows],['CAPTURED','BLOCKED','BLOCKED'])
            self.assertEqual((out/rows[0]['object_path']).read_bytes(),good.read_bytes())
            self.assertFalse(any('object_path' in r for r in rows[1:]))

    def test_stop_prevents_any_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp);stop=root/'STOP';stop.touch();out=root/'out'
            with mock.patch('sys.argv',['capture_resources','--request',str(root/'not-needed'),'--output',str(out),'--stop-file',str(stop)]),self.assertRaises(RuntimeError):c.main()
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
