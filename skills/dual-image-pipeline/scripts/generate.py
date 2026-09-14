#!/usr/bin/env python3
"""
Dual-Vendor High-Speed Image Generation Pipeline with Financial Adaptability.

Wisely adapts to the user's financial abilities:
- Tier 1 (Both AGY + Codex available): Parallel dual-vendor split for maximum speed.
- Tier 2 (Single vendor available): Routes cleanly through the available engine.
- Tier 3 (Zero-cost / No subscriptions): 100% free terminal generation via Pollinations.ai FLUX.
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
import urllib.parse
import urllib.request
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
    """Check whether Codex CLI is installed and configured."""
    auth_file = PERSONAL_HOME / "auth.json"
    if auth_file.is_file() and auth_file.stat().st_size > 10:
        return True
    return os.path.exists(CODEX_BIN) and os.access(CODEX_BIN, os.X_OK)


def check_agy_available() -> bool:
    """Check whether Antigravity agent or CLI is available in current environment."""
    agy_bin = os.environ.get("AGY_BIN", "agy")
    try:
        proc = subprocess.run(
            [agy_bin, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )
        return proc.returncode == 0
    except Exception:
        # Also check if running directly inside an active Antigravity session
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTIGRAVITY_AGENT"))


def detect_available_providers(force_free: bool = False) -> List[str]:
    """
    Wisely detect available providers according to the user's environment:
    - If force_free is True -> ['free']
    - If both AGY and Codex -> ['agy', 'codex', 'free']
    - If only AGY -> ['agy', 'free']
    - If only Codex -> ['codex', 'free']
    - If neither -> ['free'] (Zero-cost open community tier)
    """
    if force_free:
        return ["free"]

    has_agy = check_agy_available()
    has_codex = check_codex_auth()

    if has_agy and has_codex:
        return ["agy", "codex", "free"]
    if has_agy:
        return ["agy", "free"]
    if has_codex:
        return ["codex", "free"]
    return ["free"]


def generate_single_mock(output_path: Path) -> bool:
    """Write minimal image file for dry-run or unit testing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(TINY_PNG)
    return True


def is_valid_image_file(path: Path) -> bool:
    """Check whether file exists, is non-empty, and has valid image magic bytes (PNG, JPEG, WebP, Netpbm, GIF, BMP)."""
    if not path.is_file():
        return False
    try:
        if path.stat().st_size < 8:
            return False
        with open(path, "rb") as f:
            header = f.read(16)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return True
        if header.startswith(b"\xff\xd8\xff"):
            return True
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return True
        if len(header) >= 3 and header[0:1] == b"P" and header[1:2] in b"123456" and header[2:3] in (b"\n", b"\r", b" ", b"\t"):
            return True
        if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            return True
        if header.startswith(b"BM"):
            return True
        return False
    except (OSError, PermissionError):
        return False


def call_free_pollinations(prompt: str, output_path: Path, aspect_ratio: str = "9:16") -> bool:
    """
    100% Free terminal image generation via Pollinations.ai (FLUX.1 model).
    Requires zero money, zero accounts, zero API keys, and zero subscriptions.
    """
    dim_map = {
        "9:16": (768, 1376),
        "16:9": (1376, 768),
        "1:1": (1024, 1024),
    }
    width, height = dim_map.get(aspect_ratio, (768, 1376))

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "agentic-evangelism/dual-image-pipeline"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            if response.status == 200:
                data = response.read()
                if len(data) > 100:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(data)
                    return is_valid_image_file(output_path)
        return False
    except Exception:
        return False


def call_codex_cli(prompt: str, output_path: Path, aspect_ratio: str = "9:16") -> bool:
    """Generate image via Codex CLI (GPT-Image 2.5)."""
    if not os.path.exists(CODEX_BIN):
        return False

    env = os.environ.copy()
    env["CODEX_HOME"] = str(PERSONAL_HOME)

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
    """Generate image via AGY CLI (Gemini 3.1 Flash Image)."""
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


def partition_scenes(
    scenes: List[Dict[str, Any]],
    providers: List[str],
) -> List[Tuple[Dict[str, Any], str]]:
    """
    Distribute scenes across active providers.
    If dual providers (e.g. AGY + Codex), alternates between them for speed.
    If single provider or free only, routes all to that primary provider.
    """
    primary_providers = [p for p in providers if p != "free"] or ["free"]
    assignments = []
    for idx, scene in enumerate(scenes):
        provider = primary_providers[idx % len(primary_providers)]
        assignments.append((scene, provider))
    return assignments


class PipelineRunner:
    def __init__(
        self,
        style_anchor: str = DEFAULT_STYLE_ANCHOR,
        agy_workers: int = 3,
        codex_workers: int = 2,
        free_workers: int = 2,
        aspect_ratio: str = "9:16",
        force_free: bool = False,
        dry_run: bool = False,
        mock_failures: Optional[List[str]] = None,
        mock_providers: Optional[List[str]] = None,
    ):
        self.style_anchor = style_anchor
        self.agy_workers = agy_workers
        self.codex_workers = codex_workers
        self.free_workers = free_workers
        self.aspect_ratio = aspect_ratio
        self.force_free = force_free
        self.dry_run = dry_run
        self.mock_failures = set(mock_failures or [])
        self.active_providers = (
            mock_providers if mock_providers is not None
            else detect_available_providers(force_free=self.force_free)
        )

    def generate_scene(
        self,
        scene: Dict[str, Any],
        preferred_provider: str,
        output_dir: Path,
    ) -> Dict[str, Any]:
        scene_id = str(scene.get("id", "scene")).strip() or "scene"
        prompt = scene.get("prompt", "")
        rel_or_abs = Path(scene.get("image", f"{scene_id}.png"))
        output_path = rel_or_abs if rel_or_abs.is_absolute() else output_dir / rel_or_abs

        if not prompt or not str(prompt).strip():
            return {
                "id": scene_id,
                "provider": None,
                "status": "failed",
                "output": str(output_path),
                "error": f"Empty or missing prompt for '{scene_id}'. A non-empty prompt is required.",
            }

        compiled_prompt = compile_prompt(str(prompt), self.style_anchor)

        # Build fallback order starting from preferred provider, then remaining active, then free
        order = [preferred_provider]
        for p in self.active_providers:
            if p not in order:
                order.append(p)
        if "free" not in order:
            order.append("free")

        for provider in order:
            if f"{provider}:{scene_id}" in self.mock_failures:
                # Simulated failover trigger for tests
                continue

            if self.dry_run:
                success = generate_single_mock(output_path)
            elif provider == "agy":
                success = call_agy_cli(compiled_prompt, output_path, self.aspect_ratio)
            elif provider == "codex":
                success = call_codex_cli(compiled_prompt, output_path, self.aspect_ratio)
            elif provider == "free":
                success = call_free_pollinations(compiled_prompt, output_path, self.aspect_ratio)
            else:
                success = False

            if success and is_valid_image_file(output_path):
                return {
                    "id": scene_id,
                    "provider": provider,
                    "status": "success",
                    "output": str(output_path),
                }

        # Fallback to local stub if dry run
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
            "error": "All available providers exhausted or rate-limited",
        }

    def run_storyboard(
        self,
        storyboard_path: Path,
        output_dir: Path,
    ) -> Dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        data = json.loads(storyboard_path.read_text(encoding="utf-8"))

        # Check canonical Schema v2 assets first
        if "assets" in data and isinstance(data["assets"], list) and len(data["assets"]) > 0:
            raw_items = data["assets"]
            is_canonical_assets = True
        elif "scenes" in data and isinstance(data["scenes"], list) and len(data["scenes"]) > 0:
            raw_items = data["scenes"]
            is_canonical_assets = False
        else:
            raise ValueError("Storyboard contains neither 'assets' nor 'scenes'")

        seen_ids = set()
        seen_paths = set()
        items_to_generate: List[Dict[str, Any]] = []

        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise ValueError(f"Invalid item at index {idx} in storyboard: must be an object")

            raw_id = item.get("id")
            if raw_id is not None and str(raw_id).strip():
                item_id = str(raw_id).strip()
            else:
                item_id = f"item_{idx}" if is_canonical_assets else f"scene_{idx}"

            if item_id in seen_ids:
                raise ValueError(f"Duplicate item id '{item_id}' found in storyboard")
            seen_ids.add(item_id)

            prompt = item.get("prompt", "")
            if not prompt or not str(prompt).strip():
                raise ValueError(f"Item '{item_id}' has an empty or missing prompt")

            rel_or_abs = Path(item.get("image", f"{item_id}.png"))
            output_path = rel_or_abs if rel_or_abs.is_absolute() else output_dir / rel_or_abs
            resolved_str = str(output_path.resolve())
            if resolved_str in seen_paths:
                raise ValueError(f"Conflicting output path '{output_path}' between storyboard items")
            seen_paths.add(resolved_str)

            item_copy = dict(item)
            item_copy["id"] = item_id
            items_to_generate.append(item_copy)

        assignments = partition_scenes(items_to_generate, self.active_providers)
        results: List[Dict[str, Any]] = []

        total_workers = max(1, self.agy_workers + self.codex_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
            future_to_scene = {
                executor.submit(self.generate_scene, item, prov, output_dir): item
                for item, prov in assignments
            }

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
            "total_assets": len(items_to_generate),
            "total_scenes": len(data.get("scenes", items_to_generate)),
            "completed": success_count,
            "results": results,
            "active_providers": self.active_providers,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Dual-vendor and zero-cost parallel image generator (AGY, Codex, Free Pollinations)."
    )
    parser.add_argument("--storyboard", type=Path, help="Path to storyboard JSON file")
    parser.add_argument("--output-dir", type=Path, help="Output directory for storyboard images")
    parser.add_argument("--prompt", type=str, help="Single image generation prompt")
    parser.add_argument("--output", type=Path, help="Output file path for single image mode")
    parser.add_argument("--aspect-ratio", type=str, default="9:16", choices=["9:16", "16:9", "1:1"])
    parser.add_argument("--style-anchor", type=str, default=DEFAULT_STYLE_ANCHOR)
    parser.add_argument("--free", action="store_true", help="Force zero-cost free generation (no subscriptions needed)")
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
        force_free=args.free,
        dry_run=args.dry_run,
    )

    if args.storyboard:
        out_dir = args.output_dir or args.storyboard.resolve().parent / "images"
        summary = runner.run_storyboard(args.storyboard, out_dir)
        total_items = summary.get("total_assets", summary.get("total_scenes", 0))
        if summary["completed"] != total_items:
            print(f"Error: {total_items - summary['completed']} items failed", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.output:
            parser.error("--output is required when --prompt is specified")
        preferred = runner.active_providers[0] if runner.active_providers else "free"
        res = runner.generate_scene(
            {"id": "single", "prompt": args.prompt, "image": str(args.output)},
            preferred_provider=preferred,
            output_dir=args.output.parent,
        )
        if res["status"] != "success":
            print(f"Error generating image: {res.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
