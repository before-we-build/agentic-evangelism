from pathlib import Path
import sys
import unittest
from unittest.mock import patch

# Ensure skills/suno-tiktok-video/scripts is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skills' / 'suno-tiktok-video' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import doctor


class DoctorTests(unittest.TestCase):
    def test_check_python(self):
        res = doctor.check_python()
        self.assertIn('version', res)
        self.assertTrue(res['ok'])

    def test_find_tool(self):
        # python3 should always exist in test environment
        self.assertIsNotNone(doctor.find_tool('python3'))
        self.assertIsNone(doctor.find_tool('non_existent_binary_xyz123'))

    def test_check_ffmpeg_features_missing_binary(self):
        res = doctor.check_ffmpeg_features('/non/existent/path/ffmpeg')
        self.assertFalse(res['ok'])

    @patch('builtins.print')
    def test_run_doctor_missing_tools_returns_1(self, mock_print):
        # Force tools to be not found
        with patch('doctor.find_tool', return_value=None):
            code = doctor.run_doctor(json_output=True)
            self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
