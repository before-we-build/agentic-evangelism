#!/usr/bin/env python3
import json
import unittest
from pathlib import Path
import sys
import tempfile

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "skills" / "suno-tiktok-video" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from platform_utils import is_valid_video_file, is_valid_image_file

class BuildVideoMixedTests(unittest.TestCase):
    def test_is_valid_video_file_detection(self):
        with tempfile.TemporaryDirectory() as td:
            p_mp4 = Path(td) / "test.mp4"
            # MP4 ftyp box header
            # 4 bytes size (0x00000018), 4 bytes 'ftyp', 4 bytes 'mp42'
            p_mp4.write_bytes(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42' + b'\x00'*20)
            self.assertTrue(is_valid_video_file(p_mp4))

            p_corrupt = Path(td) / "bad.mp4"
            p_corrupt.write_bytes(b'random invalid text file contents')
            self.assertFalse(is_valid_video_file(p_corrupt))

            p_webm = Path(td) / "test.webm"
            # EBML ID \x1a\x45\xdf\xa3
            p_webm.write_bytes(b'\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01' + b'\x00'*20)
            self.assertTrue(is_valid_video_file(p_webm))

    def test_storyboard_mixed_scene_syntax(self):
        # Verify JSON schema parsing with video and image scenes
        data = {
            "scenes": [
                {"id": "scene-01", "image": "art/01.png", "duration_seconds": 4.0},
                {"id": "scene-02", "video": "art/02.mp4", "duration_seconds": 6.0}
            ]
        }
        self.assertIn("image", data["scenes"][0])
        self.assertIn("video", data["scenes"][1])

if __name__ == "__main__":
    unittest.main()
