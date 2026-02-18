
import unittest
import json
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Adjust import path
sys.path.append(str(Path(__file__).parent.parent))

from mcp_inventory.gui import MCPInvHandler

class MockRequest:
    def __init__(self, path):
        self.path = path
        self.makefile = MagicMock()
        
class MockServer:
    def __init__(self):
        self.server_address = ('localhost', 8080)

class TestGuiOptimization(unittest.TestCase):
    def test_api_get_full_state_structure(self):
        # Setup
        socket_mock = MagicMock()
        rfile = io.BytesIO(b"")
        wfile = io.BytesIO()
        
        # Manually instantiate and patch
        handler = MCPInvHandler.__new__(MCPInvHandler)
        handler.request = socket_mock
        handler.client_address = ('127.0.0.1', 5000)
        handler.server = MagicMock()
        handler.wfile = wfile
        handler.rfile = rfile
        handler.path = "/api/state/full"
        handler.headers = {}
        
        # Mock aggregation helpers
        handler._get_config_state_data = MagicMock(return_value={"mcpServers": {"test": {"disabled": True}}})
        handler._get_system_status_data = MagicMock(return_value={"observer": True, "mock": True})
        handler._get_logs_internal = MagicMock(return_value=[{"level": "INFO", "message": "Test"}])
        
        # Mock send_json_response
        handler.send_json_response = MagicMock()
        
        # Run
        with patch("mcp_inventory.gui.Path") as MockPath:
            mock_path_instance = MockPath.return_value
            mock_path_instance.exists.return_value = False 
            
            handler.api_get_full_state()
            
        # Verify call
        handler.send_json_response.assert_called_once()
        args = handler.send_json_response.call_args[0][0]
        
        self.assertIn("configState", args)
        self.assertIn("inventory", args)
        self.assertIn("health", args)
        self.assertIn("logs", args)
        self.assertIn("system", args)
        self.assertTrue(args["system"]["mock"])
        self.assertEqual(args["logs"][0]["message"], "Test")
        print("✅ Optimization Verification Passed: Combined state payload structure is correct.")

if __name__ == "__main__":
    unittest.main()
