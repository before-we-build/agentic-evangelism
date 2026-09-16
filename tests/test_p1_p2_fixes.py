import os
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = ROOT / "skills" / "suno-tiktok-video" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import align_lyrics
import doctor
import platform_utils
import render_karaoke


class P1P2FixesTests(unittest.TestCase):
    def test_groq_exception_sanitization_no_leak(self):
        """P1: Verify API key is redacted and no raw exception is chained in __cause__."""
        secret_key = "gsk_test_secret_key_9876543210"

        class FailingTranscriptions:
            def create(self, **kwargs):
                raise Exception(f"HTTP 401 Unauthorized: Authorization Bearer {secret_key}")

        class FailingGroq:
            def __init__(self, **kwargs):
                self.audio = types.SimpleNamespace(transcriptions=FailingTranscriptions())

        with mock.patch.dict(sys.modules, {"groq": types.SimpleNamespace(Groq=FailingGroq)}):
            with self.assertRaises(RuntimeError) as ctx:
                align_lyrics.call_groq_whisper(
                    audio_path=Path("/tmp/sample.mp3"),
                    api_key=secret_key,
                )

            err_msg = str(ctx.exception)
            self.assertNotIn(secret_key, err_msg)
            self.assertIn("[REDACTED]", err_msg)
            # Ensure __cause__ is None to prevent exception chaining leak
            self.assertIsNone(ctx.exception.__cause__)

    def test_escape_ffmpeg_filter_path(self):
        """P1: Verify FFmpeg filter path escaping handles colons, backslashes, quotes, brackets."""
        # Simulated Windows path
        win_path = r"C:\Users\Artist\Music\song.ass"
        escaped = platform_utils.escape_ffmpeg_filter_path(win_path)
        # Slashes normalized, colon escaped with backslash
        self.assertNotIn(r"\Users", escaped)
        self.assertIn("C\\:/", escaped)

        # Path with quotes and brackets
        complex_path = Path("/tmp/dir with spaces/artist's [song].ass")
        escaped_complex = platform_utils.escape_ffmpeg_filter_path(complex_path)
        self.assertIn(r"\'", escaped_complex)
        self.assertIn(r"\[", escaped_complex)
        self.assertIn(r"\]", escaped_complex)

    def test_detect_audio_attribution_human_override(self):
        """P1: Explicit user_provenance='human' must always override AI heuristics."""
        meta = {
            "format": {
                "tags": {
                    "artist": "Suno AI",
                    "comment": "https://suno.com/song/123",
                }
            }
        }
        res = platform_utils.detect_audio_attribution(
            metadata=meta,
            filename="suno_christian_demo.mp3",
            user_provenance="human"
        )
        self.assertFalse(res["is_ai"])
        self.assertFalse(res["requires_attribution"])
        self.assertEqual(res["provenance"], "human")
        self.assertEqual(res["detection_source"], "user_choice")
        self.assertIsNone(res["generator"])

    def test_detect_audio_attribution_ignores_lyrics_tags(self):
        """P1: Lyrical words matching generator names must not trigger false AI attribution."""
        meta = {
            "format": {
                "tags": {
                    "lyrics": "Listen (suno) my brother, hear the holy word",
                    "artist": "Local Church Choir",
                }
            }
        }
        res = platform_utils.detect_audio_attribution(
            metadata=meta,
            filename="church_choir.mp3",
        )
        self.assertFalse(res["is_ai"])
        self.assertFalse(res["requires_attribution"])
        self.assertIsNone(res["generator"])

    def test_align_segments_to_scenes_short_audio_no_negative_duration(self):
        """P2: Short audio with multiple scenes must never produce negative durations."""
        scenes = [
            {"image": f"{i}.png", "duration_seconds": 0.5} for i in range(4)
        ]
        segments = [{"start": 0.5, "end": 1.0, "text": "Short phrase"}]
        total_duration = 2.0

        aligned = align_lyrics.align_segments_to_scenes(scenes, segments, total_duration)
        self.assertEqual(len(aligned), 4)
        for s in aligned:
            self.assertGreater(s["duration_seconds"], 0.0)
            self.assertGreater(s["end_time"], s["start_time"])
        self.assertAlmostEqual(aligned[-1]["end_time"], total_duration, places=2)
        self.assertAlmostEqual(sum(s["duration_seconds"] for s in aligned), total_duration, places=2)

    def test_doctor_granular_capabilities(self):
        """P1: Doctor must report modular capabilities (base_video, karaoke_ass, badge, groq)."""
        groq_info = doctor.check_groq()
        self.assertIn("sdk_installed", groq_info)
        self.assertIn("key_configured", groq_info)

        disk_info = doctor.check_disk_space()
        self.assertIn("free_mb", disk_info)
        self.assertIn("ok", disk_info)

        with mock.patch("doctor.find_tool", return_value="/mock/bin/ffmpeg"):
            with mock.patch("doctor.check_ffmpeg_features", return_value={
                "libx264": True, "aac": True, "scale_filter": True,
                "pad_filter": True, "xfade_filter": True, "ass_filter": False,
                "drawtext_filter": True, "system_font": "/mock/font.ttf", "ok": True
            }):
                with mock.patch("doctor.check_python", return_value={"ok": True, "version": "3.14.0"}):
                    with mock.patch("doctor.get_downloads_dir", return_value=Path("/mock/downloads")):
                        with mock.patch("pathlib.Path.is_dir", return_value=True):
                            with mock.patch("builtins.print"):
                                code = doctor.run_doctor(json_output=True)
                                self.assertEqual(code, 0)

    def test_render_karaoke_validate_timing_metadata(self):
        """P1: Timing file validation must parse and return review metadata."""
        timing_data = {
            "version": 1,
            "reviewed": False,
            "audio_hash": "a1b2c3d4",
            "lines": [{
                "start": 0.5, "end": 1.5,
                "words": [{"text": "Христос", "start": 0.5, "end": 1.5}]
            }]
        }
        lines, meta = render_karaoke.validate_timing_data(timing_data, 2.0)
        self.assertEqual(len(lines), 1)
        self.assertFalse(meta["reviewed"])
        self.assertEqual(meta["audio_hash"], "a1b2c3d4")

    def test_safe_zone_constants(self):
        """P2: Safe zone constants must be within 1080x1920 bounds."""
        self.assertGreaterEqual(platform_utils.TIKTOK_SAFE_ZONE_X[0], 0)
        self.assertLessEqual(platform_utils.TIKTOK_SAFE_ZONE_X[1], 1080)
        self.assertGreaterEqual(platform_utils.TIKTOK_SAFE_ZONE_Y[0], 0)
        self.assertLessEqual(platform_utils.TIKTOK_SAFE_ZONE_Y[1], 1920)


if __name__ == "__main__":
    unittest.main()
