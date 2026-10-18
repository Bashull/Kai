"""Real SDK/protocol and authorization-boundary canaries; zero vendor requests."""
import asyncio
import json
import os
from pathlib import Path
import queue
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

import httpx
from mcp import Client
from PIL import Image

from kai_meshy.core import Forge, ForgeError
from kai_meshy.sdk_server import Policy, create_http_app, create_server

PACKAGE = Path(__file__).resolve().parents[1]
READ_NAMES = {
    "kai_meshy_connection_status", "kai_meshy_auth_status", "kai_meshy_balance",
    "kai_meshy_budget", "kai_meshy_list_jobs", "kai_meshy_get_job",
    "kai_meshy_list_assets", "kai_meshy_get_asset", "kai_meshy_inspect_reference", "kai_meshy_inspect_model",
}


class NoNetworkCLI:
    def auth(self):
        return {"authenticated": True, "verified": True}

    def balance(self):
        return {"balance": 71, "monthly_credits": 1, "permanent_credits": 70}

    def api(self, *args, **kwargs):
        raise AssertionError("VENDOR_API_MUST_NOT_BE_CALLED")


def body(reply):
    return json.loads(reply.content[0].text)


class SDKCanaries(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="kai_meshy_mcp_canary_")
        self.root = Path(self.temp.name)
        self.forge = Forge(self.root, cli=NoNetworkCLI())

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def test_sdk_dual_era_real_tools_and_annotation_parity(self):
        for mode, version in [("legacy", "2025-11-25"), ("auto", "2026-07-28")]:
            async with Client(create_server(self.forge, Policy()), mode=mode) as client:
                self.assertEqual(str(client.protocol_version), version)
                listing = await client.list_tools()
                self.assertEqual({t.name for t in listing.tools}, READ_NAMES)
                for tool in listing.tools:
                    self.assertTrue(tool.annotations.read_only_hint)
                    self.assertFalse(tool.annotations.open_world_hint)
                for name in ("kai_meshy_auth_status", "kai_meshy_balance", "kai_meshy_budget", "kai_meshy_list_jobs"):
                    reply = await client.call_tool(name, {})
                    self.assertFalse(reply.is_error)
                    self.assertTrue(body(reply)["ok"])
                balance = body(await client.call_tool("kai_meshy_balance", {}))["result"]
                self.assertEqual(balance["balance"], 71)
                denied = await client.call_tool("kai_meshy_create_job", {"job_id": "attempt", "source": "private"})
                self.assertTrue(denied.is_error)
        self.assertEqual(self.forge.list_jobs(), [])

    async def test_write_confirmation_and_schema_are_enforced(self):
        image = self.root / "reference.png"
        Image.frombytes("RGB", (32, 32), random.Random(717).randbytes(32 * 32 * 3)).save(image)
        async with Client(create_server(self.forge, Policy(allow_writes=True))) as client:
            no_confirm = await client.call_tool("kai_meshy_create_job", {"job_id": "canary", "source": str(image)})
            self.assertTrue(no_confirm.is_error)
            self.assertEqual(self.forge.list_jobs(), [])
            bad_id = await client.call_tool("kai_meshy_create_job", {"job_id": "../escape", "source": str(image), "confirm": True})
            self.assertTrue(bad_id.is_error)
            good = await client.call_tool("kai_meshy_create_job", {"job_id": "canary", "source": str(image), "confirm": True})
            self.assertFalse(good.is_error)
            self.assertEqual(body(good)["result"]["job"]["budget"], 36)
            cycle = await client.call_tool("kai_meshy_cycle", {"job_id": "canary", "confirm": True})
            self.assertEqual(body(cycle)["result"]["next_action"], "SUBMIT_PROTOTYPE")
            self.assertFalse(body(cycle)["result"]["paid_submission_performed"])
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertNotIn("kai_meshy_submit_stage", names)
            self.assertNotIn("kai_meshy_approve_preview", names)
            inspected = await client.call_tool("kai_meshy_inspect_reference", {"path": str(image)})
            self.assertEqual(body(inspected)["result"]["width"], 32)
            escaped = await client.call_tool("kai_meshy_inspect_reference", {"path": "/etc/passwd"})
            self.assertTrue(escaped.is_error)
            self.assertNotIn("root:", escaped.content[0].text)

    async def test_spend_allowlist_and_human_context_required_to_advertise(self):
        self.forge.spending_enabled = True
        policy = Policy(allow_writes=True, allow_spend=True, allow_approvals=True)
        async with Client(create_server(self.forge, policy)) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertNotIn("kai_meshy_submit_stage", names)
            self.assertNotIn("kai_meshy_approve_preview", names)
        self.forge.spending_job_ids = frozenset({"human-approved-canary"})
        policy = Policy(allow_writes=True, allow_spend=True, allow_approvals=True, approval_actor="synthetic-test-operator")
        async with Client(create_server(self.forge, policy)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            self.assertTrue(tools["kai_meshy_submit_stage"].annotations.destructive_hint)
            self.assertFalse(tools["kai_meshy_approve_preview"].annotations.read_only_hint)
            denied = await client.call_tool("kai_meshy_submit_stage", {"job_id": "human-approved-canary", "stage": "prototype"})
            self.assertTrue(denied.is_error)
        self.assertEqual(self.forge.budget_status()["committed_or_actual_credits"], 0)

    async def test_http_loopback_bearer_valid_and_invalid_requests(self):
        token = self.root / "http-token"
        token.write_text("synthetic-canary-token-" + "0" * 40)
        token.chmod(0o600)
        server = create_server(self.forge, Policy())
        app = create_http_app(server, token_file=token)
        with self.assertRaisesRegex(ForgeError, "HTTP_BIND_MUST_BE_LOOPBACK"):
            create_http_app(server, token_file=token, host="0.0.0.0")
        token.chmod(0o644)
        with self.assertRaisesRegex(ForgeError, "HTTP_TOKEN_FILE_MUST_BE_PRIVATE"):
            create_http_app(server, token_file=token)
        token.chmod(0o600)
        payload = {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {"_meta": {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientInfo": {"name": "canary", "version": "1"},
            "io.modelcontextprotocol/clientCapabilities": {},
        }}}
        headers = {"accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28", "mcp-method": "server/discover"}
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app, client=("127.0.0.1", 1111)), base_url="http://127.0.0.1:18772") as client:
                no_auth = await client.post("/mcp", json=payload, headers=headers)
                self.assertEqual(no_auth.status_code, 401)
                wrong = await client.post("/mcp", json=payload, headers={**headers, "authorization": "Bearer wrong"})
                self.assertEqual(wrong.status_code, 401)
                correct = await client.post("/mcp", json=payload, headers={**headers, "authorization": "Bearer " + token.read_text()})
                self.assertEqual(correct.status_code, 200)
                self.assertIn("2026-07-28", correct.json()["result"]["supportedVersions"])
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app, client=("192.0.2.1", 1111)), base_url="http://127.0.0.1:18772") as client:
                wrong_peer = await client.post("/mcp", json=payload, headers={**headers, "authorization": "Bearer " + token.read_text()})
                self.assertEqual(wrong_peer.status_code, 401)

    async def test_http_socket_loopback_auth_and_tool_call(self):
        import uvicorn
        token = self.root / "socket-token"
        token.write_text("synthetic-socket-canary-token-" + "1" * 40)
        token.chmod(0o600)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", 18772))
        except OSError:
            listener.close()
            self.skipTest("loopback18772 already in use; existing listener left untouched")
        listener.listen(16)
        listener.setblocking(False)
        app = create_http_app(create_server(self.forge, Policy()), token_file=token)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18772, log_level="error", access_log=False))
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            for _ in range(100):
                if server.started:
                    break
                if task.done():
                    await task
                await asyncio.sleep(0.02)
            self.assertTrue(server.started)
            meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                    "io.modelcontextprotocol/clientInfo": {"name": "socket-canary", "version": "1"},
                    "io.modelcontextprotocol/clientCapabilities": {}}
            packet = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "_meta": meta, "name": "kai_meshy_connection_status", "arguments": {},
            }}
            headers = {"accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2026-07-28", "mcp-method": "tools/call", "mcp-name": "kai_meshy_connection_status"}
            async with httpx.AsyncClient(base_url="http://127.0.0.1:18772", trust_env=False, timeout=5) as client:
                unauthorized = await client.post("/mcp", json=packet, headers=headers)
                self.assertEqual(unauthorized.status_code, 401)
                response = await client.post("/mcp", json=packet, headers={**headers, "authorization": "Bearer " + token.read_text()})
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()["result"]
                self.assertEqual(result["resultType"], "complete")
                self.assertFalse(result.get("isError", False))
                state = json.loads(result["content"][0]["text"])
                self.assertEqual(state["result"]["budget"]["committed_or_actual_credits"], 0)
                self.assertFalse(state["result"]["spend_enabled"])
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=5)
            listener.close()


class StdioCanary(unittest.TestCase):
    def test_real_subprocess_stdio_initialize_and_discover(self):
        # Derived from the existing KAI dual-era interactive canary: keep stdin
        # open until all responses arrive. No protocol reimplementation in server.
        with tempfile.TemporaryDirectory(prefix="kai_meshy_stdio_") as temp:
            for mode in ("legacy", "modern"):
                env = {k: v for k, v in os.environ.items() if not k.startswith("KAI_MESHY_")}
                env["PYTHONPATH"] = str(PACKAGE)
                process = subprocess.Popen(
                    [sys.executable, "-m", "kai_meshy.sdk_server", "--root", temp],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1, env=env,
                )
                output = queue.Queue()
                thread = threading.Thread(target=lambda: [output.put(line) for line in process.stdout], daemon=True)
                thread.start()

                def send(method, params, identifier):
                    packet = {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
                    process.stdin.write(json.dumps(packet) + "\n")
                    process.stdin.flush()

                def receive(identifier):
                    end = time.monotonic() + 15
                    while time.monotonic() < end:
                        try:
                            packet = json.loads(output.get(timeout=max(0.01, end - time.monotonic())))
                        except queue.Empty:
                            self.fail("stdio response timed out")
                        if packet.get("id") == identifier:
                            return packet
                    self.fail("stdio response missing")

                meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                        "io.modelcontextprotocol/clientInfo": {"name": "canary", "version": "1"},
                        "io.modelcontextprotocol/clientCapabilities": {}}
                try:
                    if mode == "legacy":
                        send("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "canary", "version": "1"}}, 1)
                    else:
                        send("server/discover", {"_meta": meta}, 1)
                    handshake = receive(1)["result"]
                    if mode == "legacy":
                        self.assertEqual(handshake["protocolVersion"], "2025-11-25")
                        process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
                        process.stdin.flush()
                    else:
                        self.assertIn("2026-07-28", handshake["supportedVersions"])
                    send("tools/list", {} if mode == "legacy" else {"_meta": meta}, 2)
                    tools = receive(2)["result"]["tools"]
                    self.assertEqual({t["name"] for t in tools}, READ_NAMES)
                    params = {"name": "kai_meshy_connection_status", "arguments": {}}
                    if mode == "modern":
                        params["_meta"] = meta
                    send("tools/call", params, 3)
                    result = receive(3)["result"]
                    self.assertFalse(result.get("isError", False))
                    state = json.loads(result["content"][0]["text"])
                    self.assertTrue(state["ok"])
                    self.assertFalse(state["result"]["spend_enabled"])
                    self.assertEqual(state["result"]["budget"]["committed_or_actual_credits"], 0)
                    if mode == "modern":
                        self.assertEqual(result["resultType"], "complete")
                finally:
                    process.stdin.close()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=5)
                    thread.join(timeout=2)
                    stderr = process.stderr.read()
                    process.stdout.close()
                    process.stderr.close()
                    self.assertEqual(process.returncode, 0, stderr[-1000:])


if __name__ == "__main__":
    unittest.main()
