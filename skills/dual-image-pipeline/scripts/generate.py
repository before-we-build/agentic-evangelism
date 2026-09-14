#!/usr/bin/env python3
"""
Dual-Vendor High-Speed Image Generation Pipeline.

Dispatches generation jobs concurrently across Antigravity (Gemini Flash Image)
and OpenAI Codex (GPT-Image 2.5 Flare/Sunburst) pools with automatic failover.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

CODEX_BIN = os.environ.get("CODEX_BIN", "/Applications/ChatGPT.app/Contents/Resources/codex")
PERSONAL_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex-personal")))

DEFAULT_STYLE_ANCHOR = (
    "cinematic 35mm photography, natural soft daylight, Kodak Portra tones, "
    "clean composition, no text, no halos, no devotional icons"
)

# Minimal 1x1 transparent PNG bytes for mock/dry-run outputs
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)


def compile_prompt(scene_prompt: str, style_anchor: str) -> str:
    """Prepend the shared style anchor to ensure cross-engine visual cohesion."""
    if not style_anchor.strip():
        return scene_prompt.strip()
    return f"{style_anchor.strip()}. {scene_prompt.strip()}"


def check_codex_auth() -> bool:
    """Check whether Codex CLI has a valid authentication configuration."""
    auth_file = PERSONAL_HOME / "auth.json"
    if auth_file.is_file() and auth_file.stat().st_size > 10:
        return True
    return os.path.exists(CODEX_BIN) and os.access(CODEX_BIN, os.X_OK)


def generate_single_mock(output_path: Path) -> bool:
    """Write minimal image file for dry-run or unit testing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(TINY_PNG)
    return True


def call_codex_cli(prompt: str, output_path: Path, aspect_ratio: str = "9:16") -> bool:
    """Generate image via Codex CLI."""
    if not os.path.exists(CODEX_BIN):
        return False

    env = os.environ.copy()
    env["CODEX_HOME"] = str(PERSONAL_HOME)

    # Resolution mapping for GPT-Image 2.5
    size_map = {
        "9:16": "1024x1792",
        "16:9": "1792x1024",
        "1:1": "1024x1024",
    }
    size = size_map.get(aspect_ratio, "1024x1792")

    cmd = [
        CODEX_BIN,
        "exec",
        "-s", "read-only",
        "--ephemeral",
        f"Generate image ({size}): {prompt}",
        "-o", str(output_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        return proc.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0
    except Exception:
        return False


def call_agy_cli(prompt: str, output_path: Path, aspect_ratio: str = "9:16") -> bool:
    """Generate image via AGY CLI if available."""
    agy_bin = os.environ.get("AGY_BIN", "agy")
    cmd = [
        agy_bin,
        "generate-image",
        "--prompt", prompt,
        "--output", str(output_path),
        "--aspect-ratio", aspect_ratio,
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        return proc.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0
    except Exception:
        return False


def partition_scenes(scenes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partition scenes between AGY and Codex pools.
    Even-indexed scenes go to AGY, odd-indexed go to Codex.
    """
    agy_batch = []
    codex_batch = []
    for idx, scene in enumerate(scenes):
        if idx % 2 == 0:
            agy_batch.append(scene)
        else:
            codex_batch.append(scene)
    return agy_batch, codex_batch


class PipelineRunner:
    def __init__(
        self,
        style_anchor: str = DEFAULT_STYLE_ANCHOR,
        agy_workers: int = 3,
        codex_workers: int = 2,
        aspect_ratio: str = "9:16",
        dry_run: bool = False,
        mock_failures: Optional[List[str]] = None,
    ):
        self.style_anchor = style_anchor
        self.agy_workers = agy_workers
        self.codex_workers = codex_workers
        self.aspect_ratio = aspect_ratio
        self.dry_run = dry_run
        self.mock_failures = set(mock_failures or [])

    def generate_scene(
        self,
        scene: Dict[str, Any],
        preferred_provider: str,
        output_dir: Path,
    ) -> Dict[str, Any]:
        scene_id = str(scene.get("id", "scene"))
        prompt = scene.get("prompt", "")
        compiled_prompt = compile_prompt(prompt, self.style_anchor)

        rel_or_abs = Path(scene.get("image", f"{scene_id}.png"))
        output_path = rel_or_abs if rel_or_abs.is_absolute() else output_dir / rel_or_abs

        providers_order = (
            ["agy", "codex"] if preferred_provider == "agy" else ["codex", "agy"]
        )

        for provider in providers_order:
            if f"{provider}:{scene_id}" in self.mock_failures:
                # Simulated failover trigger for tests
                continue

            if self.dry_run:
                success = generate_single_mock(output_path)
            elif provider == "agy":
                success = call_agy_cli(compiled_prompt, output_path, self.aspect_ratio)
            else:
                success = call_codex_cli(compiled_prompt, output_path, self.aspect_ratio)

            if success:
                return {
                    "id": scene_id,
                    "provider": provider,
                    "status": "success",
                    "output": str(output_path),
                }

        # Fallback to local stub if dry run or both failed
        if self.dry_run:
            generate_single_mock(output_path)
            return {
                "id": scene_id,
                "provider": "fallback",
                "status": "success",
                "output": str(output_path),
            }

        return {
            "id": scene_id,
            "provider": None,
            "status": "failed",
            "output": str(output_path),
            "error": "All providers exhausted or rate-limited",
        }

    def run_storyboard(
        self,
        storyboard_path: Path,
        output_dir: Path,
    ) -> Dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        data = json.loads(storyboard_path.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        if not scenes:
            raise ValueError("Storyboard contains no scenes")

        agy_scenes, codex_scenes = partition_scenes(scenes)
        results: List[Dict[str, Any]] = []

        total_workers = self.agy_workers + self.codex_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
            future_to_scene = {}

            for sc in agy_scenes:
                fut = executor.submit(self.generate_scene, sc, "agy", output_dir)
                future_to_scene[fut] = sc

            for sc in codex_scenes:
                fut = executor.submit(self.generate_scene, sc, "codex", output_dir)
                future_to_scene[fut] = sc

            for future in concurrent.futures.as_completed(future_to_scene):
                res = future.result()
                results.append(res)
                print(
                    json.dumps({
                        "id": res["id"],
                        "provider": res["provider"],
                        "status": res["status"],
                        "output": res["output"],
                    }),
                    flush=True,
                )

        success_count = sum(1 for r in results if r["status"] == "success")
        return {
            "total_scenes": len(scenes),
            "completed": success_count,
            "results": results,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Dual-vendor parallel high-speed image generator (AGY + Codex)."
    )
    parser.add_argument("--storyboard", type=Path, help="Path to storyboard JSON file")
    parser.add_argument("--output-dir", type=Path, help="Output directory for storyboard images")
    parser.add_argument("--prompt", type=str, help="Single image generation prompt")
    parser.add_argument("--output", type=Path, help="Output file path for single image mode")
    parser.add_argument("--aspect-ratio", type=str, default="9:16", choices=["9:16", "16:9", "1:1"])
    parser.add_argument("--style-anchor", type=str, default=DEFAULT_STYLE_ANCHOR)
    parser.add_argument("--agy-workers", type=int, default=3)
    parser.add_argument("--codex-workers", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true", help="Simulate generation without calling APIs")

    args = parser.parse_args()

    if not args.storyboard and not args.prompt:
        parser.error("Either --storyboard or --prompt must be provided")

    runner = PipelineRunner(
        style_anchor=args.style_anchor,
        agy_workers=args.agy_workers,
        codex_workers=args.codex_workers,
        aspect_ratio=args.aspect_ratio,
        dry_run=args.dry_run,
    )

    if args.storyboard:
        out_dir = args.output_dir or args.storyboard.resolve().parent / "images"
        summary = runner.run_storyboard(args.storyboard, out_dir)
        if summary["completed"] != summary["total_scenes"]:
            print(f"Error: {summary['total_scenes'] - summary['completed']} scenes failed", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.output:
            parser.error("--output is required when --prompt is specified")
        res = runner.generate_scene(
            {"id": "single", "prompt": args.prompt, "image": str(args.output)},
            preferred_provider="agy",
            output_dir=args.output.parent,
        )
        if res["status"] != "success":
            print(f"Error generating image: {res.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
