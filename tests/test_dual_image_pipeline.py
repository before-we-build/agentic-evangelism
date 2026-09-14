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

    def test_partition_scenes_fair_split(self):
        scenes = [{"id": f"scene_{i}"} for i in range(5)]
        agy, codex = generate.partition_scenes(scenes)
        self.assertEqual([s["id"] for s in agy], ["scene_0", "scene_2", "scene_4"])
        self.assertEqual([s["id"] for s in codex], ["scene_1", "scene_3"])

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

            runner = generate.PipelineRunner(dry_run=True)
            result = runner.run_storyboard(storyboard, out_dir)

            self.assertEqual(result["total_scenes"], 4)
            self.assertEqual(result["completed"], 4)
            for i in range(4):
                img = out_dir / f"img_{i}.png"
                self.assertTrue(img.is_file())
                self.assertTrue(img.stat().st_size > 10)

    def test_automatic_failover_when_primary_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            out_dir = work / "images"

            # Primary provider for even scene (0) is 'agy'.
            # We simulate that 'agy:sc_0' fails.
            runner = generate.PipelineRunner(
                dry_run=True,
                mock_failures=["agy:sc_0"],
            )

            res = runner.generate_scene(
                {"id": "sc_0", "prompt": "Test failover", "image": "sc_0.png"},
                preferred_provider="agy",
                output_dir=out_dir,
            )

            self.assertEqual(res["status"], "success")
            # Should have failed over to codex
            self.assertEqual(res["provider"], "codex")
            self.assertTrue((out_dir / "sc_0.png").is_file())

    def test_cli_dry_run_subprocess(self):
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
