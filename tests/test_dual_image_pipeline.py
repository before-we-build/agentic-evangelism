#!/usr/bin/env python3
"""Integration checks: route consent, references, adapter failures and durable resume."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import shutil
import struct
import tempfile
import time
import unittest
import zlib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "dual-image-pipeline" / "scripts" / "generate.py"
sys.path.insert(0, str(SCRIPT.parent))
import generate


def profile(kind="host_tool", **updates):
    now = time.time()
    return {"id": "host", "kind": kind, "quota_group": "account",
            "image_capability": True, "entitlement": "verified", "authorized": True,
            "subscription": {"kind": "subscription", "plan": "confirmed"},
            "evidence": {"source": "user_confirmed", "checked_at": now - 1, "expires_at": now + 600},
            "overage_disabled": True, "supports_references": True,
            "limits": {"max_parallel": 2, "initial_parallel": 2},
            "cost": {"per_request": 0}, **updates}


class DualImagePipelineTests(unittest.TestCase):
    def test_compile_prompt_injects_style_anchor(self):
        self.assertEqual(generate.compile_prompt("Sunrise", "Watercolor"), "Watercolor. Sunrise")
        self.assertEqual(generate.compile_prompt(" Sunrise ", ""), "Sunrise")

    def test_canonical_assets_generate_only_unique_images_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            board = work / "board.json"
            board.write_text(json.dumps({
                "assets": [{"id": "a", "prompt": "Sunrise", "image": "a.png"},
                           {"id": "b", "prompt": "River", "image": "b.png"}],
                "scenes": [{"image": "a.png"}, {"image": "b.png"}, {"image": "a.png"}]
            }))
            args = ["--storyboard", str(board), "--dry-run", "--max-wait-seconds", "1"]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate.main(args), 0)
            before = [(work / name).stat().st_mtime_ns for name in ("a.png", "b.png")]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate.main(args), 0)
            self.assertEqual(before, [(work / name).stat().st_mtime_ns for name in ("a.png", "b.png")])

    def test_invalid_storyboards_rejected_before_generation(self):
        cases = [
            ([{"id": "a", "prompt": "Sun"}, {"id": "a", "prompt": "Rain"}], "Duplicate"),
            ([{"id": "a", "prompt": " "}], "empty or missing"),
            ([{"id": "a", "prompt": "Sun", "image": "same.png"},
              {"id": "b", "prompt": "Rain", "image": "same.png"}], "Conflicting"),
            ([{"id": "a", "prompt": "Sun", "depends_on": ["missing"]}], "Unknown"),
            ([{"id": "a", "prompt": "Sun", "depends_on": ["a"]}], "cycle"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            for assets, error in cases:
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                    generate.prepare_jobs({"assets": assets}, work / "board.json", work)

    def test_avatars_retained_and_require_reference_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            avatar = work / "avatar.png"
            avatar.write_bytes(generate.TINY_PNG)
            jobs = generate.prepare_jobs({
                "characters": [{"id": "person", "avatar_image": "avatar.png"}],
                "assets": [{"id": "a", "prompt": "Person walking", "character_ids": ["person"]}]
            }, work / "board.json", work)
            self.assertEqual(jobs[0]["reference_images"], [str(avatar)])
            self.assertTrue(jobs[0]["requires_references"])
            self.assertIn(str(avatar), jobs[0]["reference_hashes"])
            p = profile(supports_references=False, eligible=True)
            broker = generate.Scheduler([p], work / "ledger.sqlite")
            try:
                result = broker.claim(jobs, run_id="song")
                self.assertEqual(result["leases"], [])
            finally:
                broker.close()

    def test_generated_reference_also_adds_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            jobs = generate.prepare_jobs({"assets": [
                {"id": "anchor", "prompt": "Portrait", "image": "anchor.png", "review_required": True},
                {"id": "scene", "prompt": "Walking", "reference_asset_ids": ["anchor"]}
            ]}, work / "board.json", work)
            self.assertEqual(jobs[1]["depends_on"], ["anchor"])
            self.assertEqual(jobs[1]["reference_images"], [str(work / "anchor.png")])
            self.assertTrue(jobs[1]["requires_references"])

    def test_live_cli_requires_explicit_opt_in(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--prompt", "Sunrise",
                               "--output", "/tmp/unused-artwork.png"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--allow-external-cli", proc.stderr)

    def test_plan_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "routes.json"
            path.write_text(json.dumps({"schema_version": 1, "routes": [profile()]}))
            with patch.object(generate, "Scheduler") as scheduler, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate.main(["--profiles", str(path), "--plan"]), 0)
            scheduler.assert_not_called()

    def test_dry_run_never_opens_production_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            state = work / "real.sqlite"
            with contextlib.redirect_stdout(io.StringIO()):
                result = generate.main(["--prompt", "Sunrise", "--output", str(work / "mock.png"),
                                        "--state", str(state), "--dry-run"])
            self.assertEqual(result, 0)
            self.assertFalse(state.exists())
            self.assertTrue((work / "real.sqlite.dry-run").exists())

    def test_adapter_timeout_is_ambiguous_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            job = {"id": "a", "prompt": "Sunrise", "image": str(Path(tmp) / "a.png"),
                   "reference_images": []}
            with patch.object(generate.subprocess, "run", side_effect=subprocess.TimeoutExpired("adapter", 1)) as call:
                result = generate.call_adapter(job, profile("cli", command=["adapter"]), 1)
            self.assertEqual(result["status"], "ambiguous")
            self.assertEqual(call.call_count, 1)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
    def test_adapter_stages_and_verifies_real_image_before_preserving_output(self):
        def chunk(tag, payload):
            return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload))
        png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 64, 64, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress((b"\x00" + b"\x80\xa0\xc0" * 64) * 64)) + chunk(b"IEND", b""))
        real_run = subprocess.run
        staged = []

        def adapter(command, **kwargs):
            if command == ["fake-image-adapter"]:
                request = json.loads(kwargs["input"])
                path = Path(request["output"])
                path.write_bytes(png)
                staged.append(path)
                return subprocess.CompletedProcess(command, 0, json.dumps({"status": "success", "output": str(path)}), "")
            return real_run(command, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "scene.png"
            with patch.object(generate.subprocess, "run", side_effect=adapter):
                result = generate.call_adapter({"id": "a", "prompt": "Test", "image": str(target),
                                                "reference_images": []}, profile("cli", command=["fake-image-adapter"]), 1)
            self.assertEqual(result["status"], "success")
            self.assertEqual(target.read_bytes(), png)
            self.assertTrue(staged[0].is_file())
            self.assertNotEqual(staged[0], target)

    def test_output_existing_never_overwritten_or_submitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "original.png"
            path.write_bytes(b"original")
            with patch.object(generate.subprocess, "run") as call:
                result = generate.call_adapter(
                    {"id": "a", "image": str(path)}, profile("cli"), 1)
            self.assertEqual(result["status"], "permanent_error")
            self.assertEqual(path.read_bytes(), b"original")
            call.assert_not_called()

    def test_adapter_errors_only_expose_allowlisted_fields(self):
        result = generate.clean_outcome({"status": "rate_limited", "retry_after": 30,
                                         "error": "secret", "token": "secret"})
        self.assertEqual(result, {"status": "rate_limited", "retry_after": 30})
        for delay in (float("inf"), float("nan"), 10**400, True, -1, "30"):
            with self.subTest(delay=delay):
                self.assertEqual(generate.clean_outcome({"status": "rate_limited", "retry_after": delay}),
                                 {"status": "ambiguous", "reason": "invalid_retry_after"})

    def test_host_claim_record_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            routes = work / "routes.json"
            board = work / "board.json"
            routes.write_text(json.dumps({"schema_version": 1, "routes": [profile()]}))
            board.write_text(json.dumps({"assets": [{"id": "a", "prompt": "Sunrise", "image": "a.png"}]}))
            common = ["--profiles", str(routes), "--storyboard", str(board),
                      "--state", str(work / "state.sqlite"), "--run-id", "song"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(generate.main(common + ["--action", "next"]), 0)
            lease = json.loads(output.getvalue())["leases"][0]
            source = work / "generated.png"
            source.write_bytes(generate.TINY_PNG)
            result = work / "result.json"
            result.write_text(json.dumps({"status": "success", "output": str(source)}))
            with patch.object(generate, "verify_image") as verify, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    generate.main(common + ["--action", "record", "--job-id", "a",
                                            "--token", "wrong-token", "--result", str(result)])
                verify.assert_not_called()
            self.assertFalse((work / "a.png").exists())
            with patch.object(generate, "verify_image"), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate.main(common + ["--action", "record", "--job-id", "a",
                                                          "--token", lease["token"], "--result", str(result)]), 0)
                # Repeated completion acknowledgement is safe even though target now exists.
                self.assertEqual(generate.main(common + ["--action", "record", "--job-id", "a",
                                                          "--token", lease["token"], "--result", str(result)]), 0)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                generate.main(common + ["--action", "next"])
            final = json.loads(output.getvalue())
            self.assertEqual(final["leases"], [])
            self.assertEqual(final["completed"], 1)
            self.assertTrue((work / "a.png").is_file())


if __name__ == "__main__":
    unittest.main()
