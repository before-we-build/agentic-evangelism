"""The preparation step must stay local and preserve prior workspaces."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/suno-tiktok-video/scripts/prepare_video.py"


class PrepareVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys

        sys.path.insert(0, str(SCRIPT.parent))
        spec = importlib.util.spec_from_file_location("prepare_video", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_prepares_new_workspace_without_overwriting_previous_one(self):
        with tempfile.TemporaryDirectory() as directory:
            downloads = Path(directory)
            audio = downloads / "song.mp3"
            audio.write_bytes(b"song")
            lyrics = {"duration_seconds": 5.0, "status": "found", "lyrics_candidates": [{"clean": "text"}]}
            with patch.object(self.module, "check_file_stability", return_value=True), patch.object(
                self.module, "extract", return_value=lyrics
            ):
                first = self.module.prepare(audio, "song", downloads)
                second = self.module.prepare(audio, "song", downloads)
            self.assertEqual(Path(first["workspace"]).name, "Video_song_01")
            self.assertEqual(Path(second["workspace"]).name, "Video_song_02")
            self.assertTrue(Path(first["lyrics"]).is_file())
            self.assertTrue(Path(second["lyrics"]).is_file())

    def test_rejects_audio_outside_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            downloads = root / "Download"
            downloads.mkdir()
            outside = root / "private.mp3"
            outside.write_bytes(b"song")
            with patch.object(self.module, "extract") as extract:
                with self.assertRaisesRegex(ValueError, "directly inside Downloads"):
                    self.module.prepare(outside, "song", downloads)
            extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
