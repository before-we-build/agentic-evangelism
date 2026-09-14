#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GENERATE_SCRIPT = ROOT / "skills" / "dual-image-pipeline" / "scripts" / "generate.py"

sys.path.insert(0, str(GENERATE_SCRIPT.parent))
import generate  # type: ignore


class DualImagePipelineTests(unittest.TestCase):
    def test_compile_prompt_injects_style_anchor(self):
        anchor = "cinematic 35mm, Kodak Portra"
        scene = "Gentle sunrise over green hills"
        compiled = generate.compile_prompt(scene, anchor)
        self.assertEqual(compiled, "cinematic 35mm, Kodak Portra. Gentle sunrise over green hills")

    def test_compile_prompt_empty_anchor(self):
        scene = "Mountain river flowing"
        compiled = generate.compile_prompt(scene, "")
        self.assertEqual(compiled, "Mountain river flowing")

    def test_detect_available_providers_force_free(self):
        providers = generate.detect_available_providers(force_free=True)
        self.assertEqual(providers, ["free"])

    def test_partition_scenes_fair_split_dual(self):
        scenes = [{"id": f"scene_{i}"} for i in range(4)]
        assignments = generate.partition_scenes(scenes, ["agy", "codex", "free"])
        self.assertEqual(assignments[0][1], "agy")
        self.assertEqual(assignments[1][1], "codex")
        self.assertEqual(assignments[2][1], "agy")
        self.assertEqual(assignments[3][1], "codex")

    def test_partition_scenes_single_vendor(self):
        scenes = [{"id": f"scene_{i}"} for i in range(3)]
        assignments = generate.partition_scenes(scenes, ["agy", "free"])
        for _, provider in assignments:
            self.assertEqual(provider, "agy")

    def test_partition_scenes_free_only(self):
        scenes = [{"id": f"scene_{i}"} for i in range(3)]
        assignments = generate.partition_scenes(scenes, ["free"])
        for _, provider in assignments:
            self.assertEqual(provider, "free")

    def test_dry_run_storyboard_generates_all_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            storyboard = work / "storyboard.json"
            out_dir = work / "images"

            scenes_data = [
                {"id": f"sc_{i}", "prompt": f"Test prompt {i}", "image": f"img_{i}.png"}
                for i in range(4)
            ]
            storyboard.write_text(json.dumps({"scenes": scenes_data}), encoding="utf-8")

            runner = generate.PipelineRunner(
                dry_run=True,
                mock_providers=["agy", "codex", "free"],
            )
            result = runner.run_storyboard(storyboard, out_dir)

            self.assertEqual(result["total_scenes"], 4)
            self.assertEqual(result["completed"], 4)
            for i in range(4):
                img = out_dir / f"img_{i}.png"
                self.assertTrue(img.is_file())
                self.assertTrue(img.stat().st_size > 10)

    def test_automatic_failover_down_to_free_tier(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            out_dir = work / "images"

            # Simulate failure on both primary providers (agy and codex)
            runner = generate.PipelineRunner(
                dry_run=True,
                mock_failures=["agy:sc_0", "codex:sc_0"],
                mock_providers=["agy", "codex", "free"],
            )

            res = runner.generate_scene(
                {"id": "sc_0", "prompt": "Test failover", "image": "sc_0.png"},
                preferred_provider="agy",
                output_dir=out_dir,
            )

            self.assertEqual(res["status"], "success")
            # Should have failed over down to free tier
            self.assertEqual(res["provider"], "free")
            self.assertTrue((out_dir / "sc_0.png").is_file())

    def test_cli_dry_run_subprocess_with_free_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            storyboard = work / "storyboard.json"
            out_dir = work / "images"

            scenes_data = [
                {"id": "sc_01", "prompt": "Prairie sunrise", "image": "sc_01.png"}
            ]
            storyboard.write_text(json.dumps({"scenes": scenes_data}), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(GENERATE_SCRIPT),
                    "--storyboard", str(storyboard),
                    "--output-dir", str(out_dir),
                    "--free",
                    "--dry-run",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((out_dir / "sc_01.png").is_file())


if __name__ == "__main__":
    unittest.main()
