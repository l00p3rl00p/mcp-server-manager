import unittest


class TestHealthCommandNoNameError(unittest.TestCase):
    def test_health_command_runs(self):
        # This should not crash with NameError due to missing imports (sys/json).
        from mcp_inventory import cli

        class Args:
            pass

        rc = cli.cmd_health(Args())
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()

