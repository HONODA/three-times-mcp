import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class _BridgeHandler(BaseHTTPRequestHandler):
    token = "test-token"

    def log_message(self, *_args):
        return

    def _authorized(self):
        return self.headers.get("Authorization") == f"Bearer {self.token}"

    def _json(self, body, status=200):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._authorized():
            self._json({"ok": False, "error": "unauthorized"}, 401)
            return
        if self.path == "/health":
            self._json({"ok": True, "service": "test-bridge"})
            return
        if self.path == "/v1/tools":
            self._json(
                {
                    "ok": True,
                    "tools": [
                        {
                            "name": "simple_painter_echo",
                            "description": "Echo through the fake bridge.",
                            "inputSchema": {"type": "object", "properties": {}},
                        }
                    ],
                }
            )
            return
        self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        if not self._authorized():
            self._json({"ok": False, "error": "unauthorized"}, 401)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        self._json({"ok": True, "result": {"ok": True, "echo": body}})


class SimplePainterMcpTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.bridge = ThreadingHTTPServer(("127.0.0.1", 0), _BridgeHandler)
        self.bridge_thread = threading.Thread(target=self.bridge.serve_forever, daemon=True)
        self.bridge_thread.start()
        self.descriptor = Path(self.temp_directory.name) / "bridge.json"
        self.descriptor.write_text(
            json.dumps(
                {
                    "version": 1,
                    "host": "127.0.0.1",
                    "port": self.bridge.server_port,
                    "token": _BridgeHandler.token,
                }
            ),
            encoding="utf-8",
        )
        script = Path(__file__).resolve().parents[1] / "server" / "simple_painter_mcp.py"
        environment = dict(os.environ)
        environment["SIMPLE_PAINTER_BRIDGE_FILE"] = str(self.descriptor)
        self.process = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def tearDown(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()
        self.bridge.shutdown()
        self.bridge.server_close()
        self.temp_directory.cleanup()

    def _request(self, request_id, method, params=None):
        return self._request_from(self.process, request_id, method, params)

    def _request_from(self, process, request_id, method, params=None):
        message = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        process.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            self.fail(process.stderr.read().decode("utf-8"))
        return json.loads(line)

    def test_initialize_discover_and_call(self):
        initialized = self._request(
            1,
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
        )
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "simple-painter-workbuddy")

        tools = self._request(2, "tools/list", {})["result"]["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["simple_painter_status", "simple_painter_echo"])

        called = self._request(
            3,
            "tools/call",
            {"name": "simple_painter_echo", "arguments": {"message": "你好"}},
        )["result"]
        self.assertFalse(called["isError"])
        self.assertEqual(called["structuredContent"]["echo"]["arguments"]["message"], "你好")

        status = self._request(4, "tools/call", {"name": "simple_painter_status", "arguments": {}})["result"]
        self.assertTrue(status["structuredContent"]["connected"])

        self.descriptor.unlink()
        fallback_tools = self._request(5, "tools/list", {})["result"]["tools"]
        self.assertGreater(len(fallback_tools), 10)
        disconnected = self._request(
            6,
            "tools/call",
            {"name": "simple_painter_status", "arguments": {}},
        )["result"]
        self.assertFalse(disconnected["structuredContent"]["connected"])

    def test_new_tools_forward_revision_and_native_tree_arguments(self):
        for index, (name, arguments) in enumerate([
            ('simple_painter_get_space_summaries', {'space_ids': ['project'], 'limit': 5}),
            ('simple_painter_update_organized_draft', {'draft_id': 'draft-1',
             'text': 'new', 'expected_text': 'old', 'expected_updated_at': 'revision'}),
            ('simple_painter_create_mind_map', {'nodes': [
             {'key': 'root', 'text': '主题'}, {'key': 'child', 'text': '分支', 'parent_key': 'root'}]}),
        ]):
            result = self._request(index + 20, 'tools/call', {
                'name': name, 'arguments': arguments})['result']['structuredContent']
            self.assertEqual(result['echo'], {'name': name, 'arguments': arguments})
        self.descriptor.unlink()
        names = {tool['name'] for tool in self._request(30, 'tools/list')['result']['tools']}
        self.assertIn('simple_painter_update_organized_draft', names)
        self.assertIn('simple_painter_create_mind_map', names)
        offline = self._request(31, 'tools/list')['result']['tools']
        self.assertEqual(len(offline), len({t['name'] for t in offline}))
        search = next(t for t in offline if t['name'] == 'simple_painter_search_canvas_items')
        props = search['inputSchema']['properties']
        self.assertIn('all', props['scope']['enum'])
        self.assertIn('space_ids', props)
        self.assertIn('cursor', props)
        self.assertIn('simple_painter_get_space_summaries', names)

    def test_discovers_macos_sandbox_descriptor(self):
        fake_home = Path(self.temp_directory.name) / "home"
        sandbox_descriptor = (
            fake_home
            / "Library"
            / "Containers"
            / "com.hn.threetimes2"
            / "Data"
            / "tmp"
            / "simple-painter-workbuddy-bridge.json"
        )
        sandbox_descriptor.parent.mkdir(parents=True)
        sandbox_descriptor.write_text(self.descriptor.read_text(encoding="utf-8"), encoding="utf-8")

        script = Path(__file__).resolve().parents[1] / "server" / "simple_painter_mcp.py"
        environment = dict(os.environ)
        environment.pop("SIMPLE_PAINTER_BRIDGE_FILE", None)
        environment["HOME"] = str(fake_home)
        process = subprocess.Popen(
            [sys.executable, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        try:
            status = self._request_from(
                process,
                1,
                "tools/call",
                {"name": "simple_painter_status", "arguments": {}},
            )["result"]["structuredContent"]
            self.assertTrue(status["connected"])
            self.assertEqual(status["descriptor_path"], str(sandbox_descriptor))
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    unittest.main()
