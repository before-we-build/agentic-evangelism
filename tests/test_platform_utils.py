import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

# Ensure skills/suno-tiktok-video/scripts is in sys.path
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / 'skills' / 'suno-tiktok-video' / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import platform_utils


class PlatformUtilsTests(unittest.TestCase):
    def test_detect_current_platform(self):
        plat = platform_utils.detect_platform()
        self.assertIn(plat, ('macos', 'linux', 'windows', 'wsl', 'android_termux', 'android_proot'))

    def test_detect_termux(self):
        with patch.dict(os.environ, {'TERMUX_VERSION': '0.118'}):
            self.assertEqual(platform_utils.detect_platform(), 'android_termux')

    def test_detect_windows_mock(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.platform', 'win32'), patch('os.name', 'nt'):
            self.assertEqual(platform_utils.detect_platform(), 'windows')

    def test_detect_macos_mock(self):
        with patch.dict(os.environ, {}, clear=True), patch('sys.platform', 'darwin'):
            self.assertEqual(platform_utils.detect_platform(), 'macos')

    def test_detect_linux_mock(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch('sys.platform', 'linux'), \
             patch.object(Path, 'is_dir', return_value=False), \
             patch.object(Path, 'exists', return_value=False), \
             patch.object(Path, 'is_file', return_value=False):
            self.assertEqual(platform_utils.detect_platform(), 'linux')

    def test_get_downloads_dir_returns_path(self):
        dl = platform_utils.get_downloads_dir()
        self.assertIsInstance(dl, Path)

    def test_file_stability_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            test_file = Path(tmp) / 'test.mp3'
            # File doesn't exist yet
            self.assertFalse(platform_utils.check_file_stability(test_file, wait_seconds=0.01))

            # Empty file
            test_file.touch()
            self.assertFalse(platform_utils.check_file_stability(test_file, wait_seconds=0.01))

            # Non-empty file
            test_file.write_bytes(b'ID3...' + b'0' * 100)
            self.assertTrue(platform_utils.check_file_stability(test_file, wait_seconds=0.01))

    def test_find_audio_candidates_filters_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Create hidden file
            (tmp_path / '.hidden.mp3').write_bytes(b'hidden')
            # Create non-audio file
            (tmp_path / 'lyrics.txt').write_text('lyrics')
            # Create empty audio file
            (tmp_path / 'empty.mp3').touch()

            # Create valid audio files with different mtimes
            f1 = tmp_path / 'first.mp3'
            f1.write_bytes(b'audio1')
            time.sleep(0.02)

            f2 = tmp_path / 'second.wav'
            f2.write_bytes(b'audio2')

            candidates = platform_utils.find_audio_candidates(tmp_path)
            self.assertEqual(len(candidates), 2)
            # f2 is newer than f1, so it should be first
            self.assertEqual(candidates[0]['name'], 'second.wav')
            self.assertEqual(candidates[1]['name'], 'first.mp3')


if __name__ == '__main__':
    unittest.main()
