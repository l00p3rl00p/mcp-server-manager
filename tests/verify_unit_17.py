import sys
import os
import json
import unittest
from pathlib import Path

# Adjust path to find mcp_wrapper and nexus_session_logger
sys.path.append(str(Path(__file__).parent.parent.parent / "mcp-link-library"))

from mcp_wrapper import MCPWrapper

class TestUnit17Wrapper(unittest.TestCase):
    def setUp(self):
        self.wrapper = MCPWrapper(max_response_size=5000) # Increased to allow some data in

    def test_01_http_methods_and_schema(self):
        print("Testing GET method + Schema v1...")
        req = {
            "id": "req-01",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/posts/1"
        }
        res = self.wrapper.call(req)
        self.assertEqual(res["id"], "req-01")
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], 200)
        self.assertIn("elapsed_ms", res)
        self.assertIn("bytes_in", res)
        print("✅ GET + Schema: OK")

    def test_02_projection_engine(self):
        print("Testing extract.path (Projection)...")
        req = {
            "id": "req-02",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/posts/1",
            "extract": {"path": "title"}
        }
        res = self.wrapper.call(req)
        self.assertTrue(res["ok"])
        self.assertEqual(res["extracted"], res["data"]["title"])
        self.assertIsInstance(res["extracted"], str)
        print(f"✅ Projection: OK (extracted: '{res['extracted'][:20]}...')")

    def test_03_security_blocking(self):
        print("Testing Security Filter (scheme blocking)...")
        req = {
            "id": "req-03",
            "method": "GET",
            "url": "file:///etc/passwd"
        }
        res = self.wrapper.call(req)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"]["type"], "blocked")
        print("✅ Security Blocking: OK")

    def test_04_payload_limits_and_truncation(self):
        print("Testing Payload Guard (truncation)...")
        # Request a large-ish resource with a small limit (100 bytes set in setUp)
        req = {
            "id": "req-04",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/comments"
        }
        res = self.wrapper.call(req)
        self.assertTrue(res["truncated"])
        self.assertLessEqual(res["bytes_in"], 100 + 8192) # 8KB is chunk size, but total should stay small
        print(f"✅ Truncation: OK (Truncated: {res['truncated']}, Bytes: {res['bytes_in']})")

    def test_05_error_normalization(self):
        print("Testing Error Normalization (404)...")
        req = {
            "id": "req-05",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/invalid-path-404"
        }
        res = self.wrapper.call(req)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], 404)
        self.assertEqual(res["error"]["details"]["status"], 404)
        print("✅ Error Normalization: OK")

    def test_06_timeout_trigger(self):
        print("Testing Timeout Policy...")
        req = {
            "id": "req-06",
            "method": "GET",
            "url": "https://httpbin.org/delay/5",
            "timeout_ms": 1000 # 1 second timeout for 5s delay
        }
        res = self.wrapper.call(req)
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"]["type"], "timeout")
        print("✅ Timeout Policy: OK")

    def test_07_tier_annotation(self):
        print("Testing Cost/Tier Annotation...")
        req = {"id": "req-07", "url": "https://google.com"}
        res = self.wrapper.call(req)
        self.assertEqual(res["tier"], "external")
        
        req_local = {"id": "req-07-loc", "url": "http://localhost:11434"}
        res_loc = self.wrapper.call(req_local)
        self.assertEqual(res_loc["tier"], "local")
        print("✅ Tier Annotation: OK")

if __name__ == "__main__":
    unittest.main()
