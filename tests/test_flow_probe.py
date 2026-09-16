#!/usr/bin/env python3
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "suno-tiktok-video" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from flow_probe import probe_flow_environment

class FlowProbeTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_probe_server_unreachable(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        res = probe_flow_environment()
        self.assertFalse(res["available"])
        self.assertEqual(res["mode"], "static_fallback")
        self.assertIn("Connection refused", res["reason"])

    @patch("urllib.request.urlopen")
    def test_probe_extension_disconnected(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "server": "online",
            "extension": {"connected": False, "secondsSinceLastPoll": 55.0},
            "status": "idle"
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = probe_flow_environment()
        self.assertFalse(res["available"])
        self.assertEqual(res["mode"], "static_fallback")
        self.assertIn("sleeping", res["reason"])

    @patch("urllib.request.urlopen")
    def test_probe_extension_connected_flow_ready(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({
            "server": "online",
            "extension": {
                "connected": True,
                "secondsSinceLastPoll": 1.2,
                "flowTabActive": True,
                "flowState": "in_project"
            },
            "model": "Veo 3.1 - Lite",
            "status": "idle"
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = probe_flow_environment()
        self.assertTrue(res["available"])
        self.assertEqual(res["mode"], "hybrid_i2v")
        self.assertEqual(res["model"], "Veo 3.1 - Lite")

if __name__ == "__main__":
    unittest.main()
