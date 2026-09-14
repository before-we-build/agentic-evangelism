#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "skills" / "suno-tiktok-video" / "scripts" / "align_lyrics.py"

spec = importlib.util.spec_from_file_location("align_lyrics", SCRIPT_PATH)
align_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(align_mod)


class AlignLyricsTests(unittest.TestCase):
    def test_encode_multipart_format(self):
        fields = {"model": "whisper-large-v3", "response_format": "verbose_json"}
        files = {"file": ("test.mp3", b"ID3\x03000fakeaudio", "audio/mpeg")}
        body, ct_header = align_mod.encode_multipart(fields, files)

        self.assertTrue(ct_header.startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="model"', body)
        self.assertIn(b"whisper-large-v3", body)
        self.assertIn(b'filename="test.mp3"', body)
        self.assertIn(b"Content-Type: audio/mpeg", body)

    def test_align_segments_covers_full_duration(self):
        scenes = [
            {"subidea_id": "s01", "image": "01.png", "duration_seconds": 10.0},
            {"subidea_id": "s02", "image": "02.png", "duration_seconds": 10.0},
            {"subidea_id": "s03", "image": "03.png", "duration_seconds": 10.0},
        ]
        segments = [
            {"start": 6.2, "end": 12.5, "text": "В полночной тьме я путь ищу"},
            {"start": 13.0, "end": 19.8, "text": "Среди сомнений и тревог"},
            {"start": 20.5, "end": 26.0, "text": "Но в тишине Твой голос жду"},
        ]
        total_duration = 32.5

        aligned = align_mod.align_segments_to_scenes(scenes, segments, total_duration)

        self.assertEqual(len(aligned), 3)
        # Scene 0 starts at 0.0 (covers intro)
        self.assertEqual(aligned[0]["start_time"], 0.0)
        # Scene 2 ends at total_duration
        self.assertEqual(aligned[-1]["end_time"], 32.5)

        # Sum of durations must match total_duration within 0.01s
        sum_dur = sum(s["duration_seconds"] for s in aligned)
        self.assertAlmostEqual(sum_dur, total_duration, places=2)

        # Every scene must have positive duration
        for s in aligned:
            self.assertGreater(s["duration_seconds"], 0.5)

    def test_align_single_scene(self):
        scenes = [{"image": "single.png", "duration_seconds": 5.0}]
        aligned = align_mod.align_segments_to_scenes(scenes, [], 25.0)
        self.assertEqual(len(aligned), 1)
        self.assertEqual(aligned[0]["start_time"], 0.0)
        self.assertEqual(aligned[0]["end_time"], 25.0)
        self.assertEqual(aligned[0]["duration_seconds"], 25.0)

    def test_extract_lyrics_text_from_storyboard(self):
        sb_data = {
            "central_message": "Hope in Christ",
            "subideas": [
                {"summary": "Walking through valley", "evidence": "lines 1-2"},
                {"summary": "Morning sunrise", "evidence": "lines 3-4"},
            ]
        }
        text = align_mod.extract_lyrics_text_from_storyboard(sb_data)
        self.assertIn("Hope in Christ", text)
        self.assertIn("Walking through valley", text)
        self.assertIn("Morning sunrise", text)

    def test_cli_dry_run_updates_storyboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            audio = work / "sample.wav"
            audio.write_bytes(b"RIFF" + b"0" * 200)

            sb_file = work / "storyboard.json"
            out_file = work / "aligned_storyboard.json"

            initial_data = {
                "schema_version": 2,
                "scenes": [
                    {"image": "img1.png", "duration_seconds": 5.0},
                    {"image": "img2.png", "duration_seconds": 5.0},
                ]
            }
            sb_file.write_text(json.dumps(initial_data), encoding="utf-8")

            proc = subprocess.run([
                sys.executable, str(SCRIPT_PATH),
                "--audio", str(audio),
                "--storyboard", str(sb_file),
                "--output", str(out_file),
                "--dry-run",
            ], capture_output=True, text=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_file.is_file())

            updated_data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(updated_data["timing_basis"], "simulated_aligned")
            self.assertEqual(len(updated_data["scenes"]), 2)
            self.assertIn("start_time", updated_data["scenes"][0])

    def test_cli_missing_api_key_exits_gracefully_without_strict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            audio = work / "sample.mp3"
            audio.write_bytes(b"ID3" + b"0" * 200)

            sb_file = work / "storyboard.json"
            sb_file.write_text(json.dumps({"scenes": [{"image": "1.png", "duration_seconds": 5.0}]}), encoding="utf-8")

            proc = subprocess.run([
                sys.executable, str(SCRIPT_PATH),
                "--audio", str(audio),
                "--storyboard", str(sb_file),
            ], capture_output=True, text=True, env={})

            self.assertEqual(proc.returncode, 0)
            self.assertIn("GROQ_API_KEY environment variable is not set", proc.stderr)

    def test_cli_missing_api_key_fails_with_strict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            audio = work / "sample.mp3"
            audio.write_bytes(b"ID3" + b"0" * 200)

            sb_file = work / "storyboard.json"
            sb_file.write_text(json.dumps({"scenes": [{"image": "1.png", "duration_seconds": 5.0}]}), encoding="utf-8")

            proc = subprocess.run([
                sys.executable, str(SCRIPT_PATH),
                "--audio", str(audio),
                "--storyboard", str(sb_file),
                "--strict",
            ], capture_output=True, text=True, env={})

            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
