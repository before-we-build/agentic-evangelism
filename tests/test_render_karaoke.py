import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "suno-tiktok-video" / "scripts" / "render_karaoke.py"
spec = importlib.util.spec_from_file_location("render_karaoke", SCRIPT)
karaoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(karaoke)


class RenderKaraokeTests(unittest.TestCase):
    def test_ass_highlight_and_validation(self):
        lines = [{
            "start": 1.0, "end": 2.0,
            "words": [
                {"text": "Бо", "start": 1.0, "end": 1.25},
                {"text": "Господь!", "start": 1.5, "end": 2.0},
            ],
        }]
        validated = karaoke.validate_lines({"lines": lines}, 3.0)
        result = karaoke.make_ass(validated, 1080, 1920)
        self.assertIn(r"{\kf25}Бо", result)
        self.assertIn(r"{\k25} ", result)
        self.assertIn("Господь!", result)
        with self.assertRaises(ValueError):
            karaoke.validate_lines({"lines": lines + lines}, 3.0)
        self.assertEqual(karaoke.escape_ass(r"{bad}\tag"), "｛bad｝＼tag")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg needed")
    def test_burns_new_video_and_preserves_original_audio_codec(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / "source.mp4"
            target = work / "karaoke.mp4"
            timing = work / "timing.json"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                "-f", "lavfi", "-i", "color=c=navy:s=108x192:r=25:d=2",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(source),
            ], check=True)
            original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
            timing.write_text(json.dumps({"lines": [{
                "start": 0.25, "end": 1.5,
                "words": [
                    {"text": "Бо", "start": 0.25, "end": 0.6},
                    {"text": "Господь", "start": 0.65, "end": 1.5},
                ],
            }]}), encoding="utf-8")
            run = subprocess.run([
                sys.executable, str(SCRIPT), "--video", str(source),
                "--timing", str(timing), "--output", str(target),
            ], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(target.is_file())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original_digest)
            source_info = karaoke.probe(source, "ffprobe")
            target_info = karaoke.probe(target, "ffprobe")
            self.assertEqual(karaoke.video_details(source_info)[:2], karaoke.video_details(target_info)[:2])
            self.assertAlmostEqual(karaoke.video_details(source_info)[2],
                                   karaoke.video_details(target_info)[2], delta=0.15)
            source_audio = next(s for s in source_info["streams"] if s["codec_type"] == "audio")
            target_audio = next(s for s in target_info["streams"] if s["codec_type"] == "audio")
            self.assertEqual(source_audio["codec_name"], target_audio["codec_name"])
            again = subprocess.run([
                sys.executable, str(SCRIPT), "--video", str(source),
                "--timing", str(timing), "--output", str(target),
            ], capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertIn("new file", again.stderr)


if __name__ == "__main__":
    unittest.main()
