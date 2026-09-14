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

    def test_detect_audio_attribution_suno(self):
        res = platform_utils.detect_audio_attribution({'format': {'tags': {'artist': 'Suno'}}}, filename='song.mp3', lang='ru')
        self.assertEqual(res['generator'], 'suno')
        self.assertTrue(res['is_ai'])
        self.assertEqual(res['attribution_text'], 'Музыка: Suno AI')
        self.assertIn('#sunoai', res['caption_text'])
        self.assertTrue(res['requires_ai_toggle'])

        # Ukrainian
        res_uk = platform_utils.detect_audio_attribution(filename='suno_test.mp3', lang='uk')
        self.assertEqual(res_uk['attribution_text'], 'Музика: Suno AI')
        self.assertIn('створена за допомогою', res_uk['caption_text'])

        # English
        res_en = platform_utils.detect_audio_attribution({'format': {'tags': {'comment': 'https://suno.com/song/123'}}}, lang='en')
        self.assertEqual(res_en['attribution_text'], 'Music: Suno AI')
        self.assertIn('Music created with Suno AI', res_en['caption_text'])

    def test_detect_audio_attribution_all_generators(self):
        cases = [
            ('udio', {'format': {'tags': {'artist': 'Udio'}}}, 'Музыка: Udio AI'),
            ('mubert', {'format': {'tags': {'comment': 'mubert.com'}}}, 'Музыка: Mubert AI (mubert.com)'),
            ('aiva', {'format': {'tags': {'album': 'AIVA Soundtrack'}}}, 'Музыка: AIVA AI'),
            ('boomy', {'format': {'tags': {'artist': 'Boomy Artist'}}}, 'Музыка: Boomy AI'),
            ('soundraw', {'format': {'tags': {'comment': 'https://soundraw.io'}}}, 'Музыка: Soundraw AI'),
            ('musicgen', {'format': {'tags': {'encoder': 'Audiocraft / MusicGen'}}}, 'Музыка: Meta MusicGen'),
            ('yue', {}, 'Музыка: YuE AI', 'yue_sample.mp3'),
        ]
        for item in cases:
            gen_id, meta, expected_text = item[0], item[1], item[2]
            fname = item[3] if len(item) > 3 else None
            res = platform_utils.detect_audio_attribution(meta, filename=fname, lang='ru')
            self.assertEqual(res['generator'], gen_id, f"Failed for {gen_id}")
            self.assertEqual(res['attribution_text'], expected_text)
            self.assertEqual(res['provenance'], 'ai')
            self.assertTrue(res['is_ai'])
            self.assertTrue(res['requires_ai_toggle'])
            self.assertTrue(res['requires_attribution'])

    def test_detect_audio_attribution_clean_audio(self):
        res = platform_utils.detect_audio_attribution(
            {'format': {'tags': {'artist': 'Church Choir', 'title': 'Amazing Grace'}}},
            filename='hymn.mp3'
        )
        self.assertIsNone(res['generator'])
        self.assertFalse(res['is_ai'])
        self.assertEqual(res['provenance'], 'unknown')
        self.assertIsNone(res['attribution_text'])
        self.assertFalse(res['requires_attribution'])

        # Explicit human provenance
        res_human = platform_utils.detect_audio_attribution(
            filename='live_recording.wav',
            user_provenance='human'
        )
        self.assertEqual(res_human['provenance'], 'human')
        self.assertFalse(res_human['is_ai'])

    def test_is_valid_image_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            # Empty file
            f_empty = p / "empty.png"
            f_empty.write_bytes(b"")
            self.assertFalse(platform_utils.is_valid_image_file(f_empty))

            # HTML mock/error
            f_html = p / "error.png"
            f_html.write_text("<!DOCTYPE html><html><body>Error 500</body></html>", encoding="utf-8")
            self.assertFalse(platform_utils.is_valid_image_file(f_html))

            # Valid PNG header
            f_png = p / "valid.png"
            f_png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"0" * 20)
            self.assertTrue(platform_utils.is_valid_image_file(f_png))

            # Valid JPEG header
            f_jpg = p / "valid.jpg"
            f_jpg.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
            self.assertTrue(platform_utils.is_valid_image_file(f_jpg))

    def test_find_system_font(self):
        font = platform_utils.find_system_font()
        # On mac, Arial or Helvetica should be found
        if sys.platform == 'darwin':
            self.assertIsNotNone(font)
            self.assertTrue(font.is_file())

        # Test mocked android platform
        with patch('platform_utils.detect_platform', return_value='android_termux'), \
             patch.object(Path, 'is_file', return_value=True):
            f = platform_utils.find_system_font('android_termux')
            self.assertEqual(f, Path('/system/fonts/Roboto-Regular.ttf'))


if __name__ == '__main__':
    unittest.main()
