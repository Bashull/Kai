from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"
APP = ROOT / "app.mjs"
LAUNCHER = ROOT / "qwen-edit"
INSTALLER = ROOT / "install.sh"


class ProxyContractTests(unittest.TestCase):
    def test_proxy_module_exists_and_rewrites_gradio_root(self):
        self.assertTrue(SERVER.is_file())
        spec = importlib.util.spec_from_file_location("kai_proxy", SERVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.upstream_path("/hf/config"), "/config")
        body = module.rewrite_config(b'{"root":"https://old","x":1}', "http://127.0.0.1:7860/hf")
        self.assertEqual(__import__("json").loads(body)["root"], "http://127.0.0.1:7860/hf")

    def test_pwa_uses_local_authenticated_proxy(self):
        app = APP.read_text(encoding="utf-8")
        self.assertIn('const SPACE = `${location.origin}/hf`;', app)
        self.assertNotIn('const SPACE = "Bashull/Qwen-Image-Edit-2511-LoRAs-Fast";', app)

    def test_launcher_and_installer_ship_proxy(self):
        launcher = LAUNCHER.read_text(encoding="utf-8")
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('python "$APP/server.py"', launcher)
        self.assertNotIn("python -m http.server", launcher)
        self.assertIn("server.py", installer)

    def test_proxy_never_accepts_arbitrary_upstream(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("bashull-qwen-image-edit-2511-loras-fast.hf.space", src)
        self.assertNotIn("urlparse(self.path).netloc", src)


if __name__ == "__main__":
    unittest.main()

# Runtime wiring contract: main must attach the vault token to the handler class,
# because functools.partial attributes are not inherited by handler instances.
class ProxyRuntimeWiringTests(unittest.TestCase):
    def test_main_sets_handler_class_token_before_server_start(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn("KaiHandler.vault_token = token", src)


class ProxyStreamingContractTests(unittest.TestCase):
    def test_stream_without_content_length_closes_local_connection(self):
        src = SERVER.read_text(encoding="utf-8")
        self.assertIn('self.send_header("Connection", "close")', src)
        self.assertIn("self.close_connection = True", src)
