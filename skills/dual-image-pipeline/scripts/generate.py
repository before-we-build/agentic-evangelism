#!/usr/bin/env python3
"""Schedule verified image routes; reserve host calls or execute explicit adapters."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import codex_status
import profiles as route_profiles
from scheduler import Scheduler


DEFAULT_STYLE_ANCHOR = (
    "cinematic 35mm photography, natural soft daylight, Kodak Portra tones, "
    "clean composition, no text, no halos, no devotional icons"
)
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x00\x00"
    b"\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB\x82"
)
OUTCOMES = {"success", "review_required", "rate_limited", "transient_error",
            "quota_exhausted", "unauthorized", "permanent_error", "ambiguous"}


def compile_prompt(scene_prompt: str, style_anchor: str) -> str:
    return f"{style_anchor.strip()}. {scene_prompt.strip()}" if style_anchor.strip() else scene_prompt.strip()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_image_file(path: Path) -> bool:
    if not path.is_file():
        return False
    with path.open("rb") as stream:
        header = stream.read(12)
    return (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff") or
            (header.startswith(b"RIFF") and header[8:12] == b"WEBP"))


def verify_image(path: Path) -> None:
    if not is_valid_image_file(path):
        raise ValueError("Output is not a PNG, JPEG, or WebP image")
    if not shutil.which("ffprobe") or not shutil.which("ffmpeg"):
        raise ValueError("ffprobe and ffmpeg required to validate real artwork")
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                           "-of", "json", str(path)], capture_output=True, text=True, timeout=20)
    streams = json.loads(proc.stdout).get("streams", []) if proc.returncode == 0 else []
    if not streams or streams[0].get("width", 0) < 64 or streams[0].get("height", 0) < 64:
        raise ValueError("Missing dimensions or placeholder-sized artwork")
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                              "-frames:v", "1", "-f", "null", "-"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
    if decoded.returncode:
        raise ValueError("Image cannot be fully decoded")


def prepare_jobs(data: dict, board: Path, output_dir: Path, style_anchor="") -> list[dict]:
    raw = data.get("assets") or data.get("scenes")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Storyboard contains neither assets nor scenes")
    characters = {}
    for char in data.get("characters", []):
        cid = char["id"]
        if cid in characters:
            raise ValueError(f"Duplicate character id: {cid}")
        characters[cid] = char.get("avatar_image")
    ids, paths, jobs = set(), set(), []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("Each storyboard item must be an object")
        job_id = str(item.get("id", f"item_{index}")).strip()
        if not job_id or job_id in ids:
            raise ValueError(f"Duplicate item id or empty id: {job_id}")
        ids.add(job_id)
        prompt = item.get("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Item {job_id} has an empty or missing prompt")
        target = Path(item.get("image", f"{job_id}.png"))
        target = (target if target.is_absolute() else output_dir / target).absolute()
        if target.is_symlink():
            raise ValueError("Image destination cannot be a symlink")
        target = target.resolve()
        if target in paths:
            raise ValueError(f"Conflicting output path: {target}")
        paths.add(target)
        refs = list(item.get("reference_images", []))
        for cid in item.get("character_ids", []):
            if cid not in characters:
                raise ValueError(f"Unknown character: {cid}")
            if characters[cid]:
                refs.append(characters[cid])
        resolved, hashes = [], {}
        for ref in refs:
            path = Path(ref)
            path = (path if path.is_absolute() else board.parent / path).resolve()
            if not is_valid_image_file(path):
                raise ValueError(f"Missing or invalid image reference: {path}")
            if str(path) not in resolved:
                resolved.append(str(path))
                hashes[str(path)] = digest(path)
        job = {**item, "id": job_id, "prompt": compile_prompt(prompt, style_anchor),
               "image": str(target), "reference_images": resolved, "reference_hashes": hashes}
        # Character/reference identity stays in the fingerprint on resume.
        generated_refs = item.get("reference_asset_ids", [])
        if not isinstance(generated_refs, list) or not all(isinstance(r, str) for r in generated_refs):
            raise ValueError("reference_asset_ids must be a list of IDs")
        dependencies = item.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(d, str) for d in dependencies):
            raise ValueError("depends_on must be a list of IDs")
        job["depends_on"] = list(dict.fromkeys(dependencies + generated_refs))
        job["requires_references"] = bool(resolved or generated_refs or item.get("requires_references"))
        for key in ("review_required", "reviewed", "requires_references"):
            if key in item and not isinstance(item[key], bool):
                raise ValueError(f"{key} must be boolean")
        if "allowed_routes" in item and (not isinstance(item["allowed_routes"], list) or
                                         not all(isinstance(r, str) for r in item["allowed_routes"])):
            raise ValueError("allowed_routes must be a list of route IDs")
        jobs.append(job)
    by_id = {job["id"]: job for job in jobs}
    for job in jobs:
        for ref_id in job.get("reference_asset_ids", []):
            if ref_id not in by_id:
                raise ValueError(f"Unknown reference asset: {ref_id}")
            job["reference_images"].append(by_id[ref_id]["image"])
    Scheduler._validate_jobs(jobs)
    return jobs


def dry_profiles() -> list[dict]:
    now = time.time()
    return [{"id": "mock", "kind": "local", "quota_group": "dry-run",
             "eligible": True, "supports_references": True,
             "subscription": {"kind": "local", "plan": "offline simulation"},
             "limits": {"max_parallel": 4, "initial_parallel": 4},
             "evidence": {"source": "user_confirmed", "checked_at": now - 1, "expires_at": now + 3600},
             "cost": {"per_request": 0}, "timeout_seconds": 600}]


def clean_outcome(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("status") not in OUTCOMES:
        return {"status": "ambiguous", "reason": "adapter_result_invalid"}
    # Never copy arbitrary adapter logs/errors into shared output.
    result = {"status": value["status"]}
    if isinstance(value.get("output"), str):
        result["output"] = value["output"]
    delay = value.get("retry_after")
    if delay is not None:
        try:
            valid_delay = (not isinstance(delay, bool) and isinstance(delay, (int, float))
                           and math.isfinite(delay) and delay >= 0)
        except OverflowError:
            valid_delay = False
        if not valid_delay:
            return {"status": "ambiguous", "reason": "invalid_retry_after"}
        result["retry_after"] = delay
    return result


def preserve_output(source: Path, target: Path) -> str:
    verify_image(source)
    if source.resolve() == target.resolve():
        return str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents an unrelated/concurrent run from overwriting an original.
    with target.open("xb") as dest, source.open("rb") as src:
        shutil.copyfileobj(src, dest)
    verify_image(target)
    return str(target)


def call_adapter(job: dict, profile: dict, attempt: int, *, dry_run=False) -> dict:
    target = Path(job["image"])
    if target.exists() or target.is_symlink():
        return {"status": "permanent_error", "reason": "destination_exists"}
    target.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        with target.open("xb") as stream:
            stream.write(TINY_PNG)
        return {"status": "success", "output": str(target)}
    if profile["kind"] == "host_tool":
        return {"status": "permanent_error", "reason": "use_next_record_for_host_tool"}
    for reference in job["reference_images"]:
        if not is_valid_image_file(Path(reference)):
            return {"status": "permanent_error", "reason": "reference_missing"}
    stage = target.with_name(f"{target.stem}.attempt-{uuid.uuid4().hex}{target.suffix or '.png'}")
    payload = {"id": job["id"], "prompt": job["prompt"], "output": str(stage),
               "reference_images": job["reference_images"], "attempt": attempt}
    try:
        proc = subprocess.run(profile["command"], input=json.dumps(payload), capture_output=True,
                              text=True, timeout=profile.get("timeout_seconds", 600))
    except subprocess.TimeoutExpired:
        return {"status": "ambiguous", "reason": "adapter_timeout_check_original_request"}
    except OSError:
        return {"status": "permanent_error", "reason": "adapter_cannot_start"}
    try:
        result = clean_outcome(json.loads(proc.stdout))
    except (ValueError, TypeError):
        return {"status": "ambiguous", "reason": "adapter_no_structured_result"}
    if result["status"] in {"success", "review_required"}:
        if proc.returncode != 0:
            return {"status": "ambiguous", "reason": "adapter_exit_conflicts_with_success"}
        # A configured adapter must honor the staged destination contract.
        if Path(result.get("output", str(stage))).resolve() != stage.resolve():
            return {"status": "ambiguous", "reason": "adapter_output_path_mismatch"}
        try:
            result["output"] = preserve_output(stage, target)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return {"status": "ambiguous", "reason": "output_not_verified_preserve_attempt"}
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--probe-codex", action="store_true")
    parser.add_argument("--refresh-codex-status", action="store_true")
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prompt")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--style-anchor", default="")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--action", choices=["run", "next", "record", "status"], default="run")
    parser.add_argument("--job-id")
    parser.add_argument("--token")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--max-in-flight", type=int, default=8)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-wait-seconds", type=float, default=60)
    parser.add_argument("--allow-external-cli", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    broker = None
    try:
        if args.discover:
            print(json.dumps(route_profiles.discover(), indent=2)); return 0
        if args.probe_codex:
            print(json.dumps(codex_status.probe(), indent=2)); return 0
        if args.action == "run" and not args.plan and not args.dry_run and not args.allow_external_cli:
            parser.error("Live CLI generation requires --allow-external-cli; use next/record for host tools")
        if args.profiles:
            raw = json.loads(args.profiles.read_text(encoding="utf-8"))
            if args.refresh_codex_status:
                codex_status.refresh(raw["routes"], codex_status.probe())
            routes = route_profiles.normalize_profiles(raw)
        elif args.dry_run:
            routes = dry_profiles()
        else:
            parser.error("--profiles is required; installed binaries do not establish image access")
        if args.plan:
            print(json.dumps(route_profiles.plan(routes, args.max_in_flight), ensure_ascii=False, indent=2))
            return 0
        if args.storyboard:
            board = args.storyboard.resolve()
            data = json.loads(board.read_text(encoding="utf-8"))
            output_dir = args.output_dir or board.parent
        elif args.prompt and args.output:
            board = args.output.resolve().parent / "single-image.json"
            data = {"assets": [{"id": "single", "prompt": args.prompt, "image": str(args.output.resolve())}]}
            output_dir = args.output.resolve().parent
        else:
            parser.error("--storyboard or both --prompt and --output are required")
        jobs = prepare_jobs(data, board, output_dir, args.style_anchor)
        if args.dry_run:
            for job in jobs:
                job.pop("allowed_routes", None)
        if args.action == "run" and not args.dry_run and any(r["eligible"] and r["kind"] == "host_tool" for r in routes):
            parser.error("Host routes require --action next and record via the exposed image tool")
        if not args.state and not args.dry_run:
            parser.error("--state is required; share one private SQLite ledger across account routes")
        state = args.state or output_dir / ".image-dry-run.sqlite"
        if args.dry_run and args.state:
            state = args.state.with_name(args.state.name + ".dry-run")
        run_id = args.run_id or hashlib.sha256(str(board).encode()).hexdigest()[:24]
        # Dry-run reservations must not consume or match the real run.
        if args.dry_run:
            run_id = "dry-run:" + run_id
        broker = Scheduler(routes, state, max_in_flight=args.max_in_flight,
                           max_attempts=args.max_attempts, max_wait_seconds=args.max_wait_seconds)
        if args.action == "next":
            result = broker.claim(jobs, run_id=run_id)
            by_id = {job["id"]: job for job in jobs}
            for lease in result["leases"]:
                lease["job"] = by_id[lease["job_id"]]
            result["run_id"] = run_id
        elif args.action == "record":
            if not args.job_id or not args.token or not args.result:
                parser.error("record requires --job-id --token --result")
            outcome = clean_outcome(json.loads(args.result.read_text(encoding="utf-8")))
            job = next((job for job in jobs if job["id"] == args.job_id), None)
            if job is None:
                parser.error("Unknown --job-id")
            lease = broker.validate_record(run_id=run_id, job_id=args.job_id,
                                           token=args.token, jobs=jobs)
            if lease["status"] not in {"in_flight", "ambiguous"}:
                print(json.dumps(lease["result"], ensure_ascii=False, indent=2))
                return 0
            if outcome["status"] in {"success", "review_required"}:
                try:
                    outcome["output"] = preserve_output(Path(outcome["output"]), Path(job["image"]))
                except (OSError, KeyError, ValueError, subprocess.TimeoutExpired):
                    outcome = {"status": "ambiguous", "reason": "output_not_verified"}
            result = broker.record(run_id=run_id, job_id=args.job_id, token=args.token, outcome=outcome)
        elif args.action == "status":
            result = broker.snapshot(jobs, run_id=run_id)
        else:
            result = broker.run(jobs, lambda job, route, attempt: call_adapter(
                job, route, attempt, dry_run=args.dry_run), run_id=run_id)
        result["dry_run"] = args.dry_run
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.action == "run" and result.get("completed", 0) != len(jobs):
            return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    finally:
        if broker:
            broker.close()


if __name__ == "__main__":
    sys.exit(main())
