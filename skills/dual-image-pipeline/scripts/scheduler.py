"""Persistent, conservative image request reservations for CLI and host tools.

The broker knows verified limits supplied by its caller; it does not discover a
subscription. One SQLite file must be shared by all callers using an account.
Every attempt consumes a reservation, including failures and unknown outcomes.
"""

from __future__ import annotations

import concurrent.futures
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import time
from typing import Any, Callable
import uuid


REVIEW_FIELDS = {"reviewed", "review_token"}


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


def _profile_hash(profile: dict) -> str:
    identity = {"id", "kind", "quota_group", "command", "model", "model_id",
                "image_model", "supports_references", "tool", "tool_name",
                "endpoint", "base_url", "size", "quality", "aspect_ratio",
                "generation_options", "provider"}
    return _hash({key: value for key, value in profile.items() if key in identity})


def _decimal(value: Any) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Costs and balances must be finite and nonnegative")
    return result


class Scheduler:
    """Reserve first, execute elsewhere, then record with the original token.

    ``claim`` is suitable for a short-lived CLI or a host image tool. Leases are
    never automatically retried after expiration: their outcome is ambiguous.
    ``record`` accepts a late result for the original lease. ``run`` is a thread
    pool convenience wrapper over exactly these same operations.
    """

    def __init__(self, profiles: list[dict], state_path: Path, *,
                 max_in_flight: int = 8, max_attempts: int = 3,
                 max_wait_seconds: float = 60, clock: Callable = time.time,
                 sleeper: Callable = time.sleep):
        if (type(max_in_flight) is not int or max_in_flight < 1
                or type(max_attempts) is not int or max_attempts < 1):
            raise ValueError("Concurrency and attempt limits must be positive integers")
        try:
            valid_wait = (not isinstance(max_wait_seconds, bool)
                          and isinstance(max_wait_seconds, (int, float))
                          and math.isfinite(max_wait_seconds) and max_wait_seconds >= 0)
        except (OverflowError, TypeError, ValueError):
            valid_wait = False
        if not valid_wait:
            raise ValueError("Wait limit must be a finite nonnegative number")
        self.profiles = {profile["id"]: dict(profile) for profile in profiles}
        if len(self.profiles) != len(profiles):
            raise ValueError("Duplicate provider route IDs")
        self.max_in_flight = max_in_flight
        self.max_attempts = max_attempts
        self.max_wait_seconds = max_wait_seconds
        self.clock, self.sleeper = clock, sleeper
        self._digest_cache: dict[tuple, str] = {}
        state_path = Path(state_path)
        state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            # Create new journals privately without changing an existing file's
            # permissions. SQLite sidecars inherit the database mode on POSIX.
            fd = os.open(state_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        self.db = sqlite3.connect(state_path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS quota_groups (
                group_id TEXT PRIMARY KEY, currency TEXT NOT NULL DEFAULT 'USD',
                max_parallel INTEGER NOT NULL,
                parallel_limit INTEGER NOT NULL, clean_successes INTEGER NOT NULL DEFAULT 0,
                rpm INTEGER, rpd INTEGER, remaining INTEGER, balance_checked REAL,
                budget TEXT, budget_checked REAL, cooldown_until REAL NOT NULL DEFAULT 0,
                limits_checked REAL NOT NULL, reset_at REAL,
                blocked_reason TEXT, blocked_checked REAL
            );
            CREATE TABLE IF NOT EXISTS jobs (
                run_id TEXT NOT NULL, job_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
                status TEXT NOT NULL, route_id TEXT, profile_hash TEXT, token TEXT,
                attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at REAL NOT NULL DEFAULT 0,
                review_required INTEGER NOT NULL DEFAULT 0, image TEXT, result TEXT,
                PRIMARY KEY (run_id, job_id, fingerprint)
            );
            CREATE TABLE IF NOT EXISTS reservations (
                token TEXT PRIMARY KEY, run_id TEXT NOT NULL, job_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, route_id TEXT NOT NULL, group_id TEXT NOT NULL,
                created_at REAL NOT NULL, expires_at REAL NOT NULL, cost TEXT NOT NULL,
                status TEXT NOT NULL, outcome TEXT
            );
            CREATE INDEX IF NOT EXISTS reservation_quota
                ON reservations(group_id, created_at);
            CREATE INDEX IF NOT EXISTS reservation_active ON reservations(status);
            CREATE TABLE IF NOT EXISTS affinity (
                run_id TEXT NOT NULL, affinity_group TEXT NOT NULL, route_id TEXT NOT NULL,
                PRIMARY KEY (run_id, affinity_group)
            );
        """)
        columns = {row["name"] for row in self.db.execute("PRAGMA table_info(quota_groups)")}
        if "currency" not in columns:
            self.db.close()
            raise ValueError("Legacy quota ledger has no recorded currency; reconcile its balances and outstanding reservations before an explicit currency-aware migration")
        try:
            self._sync_groups()
        except BaseException:
            self.db.close()
            raise

    def close(self) -> None:
        self.db.close()

    def _sync_groups(self) -> None:
        """A newer verified snapshot may replenish balances; time alone cannot."""
        groups: dict[str, list[dict]] = {}
        for profile in self.profiles.values():
            # An exhausted route is ineligible to execute but still supplies a
            # verified shared-account snapshot that its aliases must observe.
            evidence = profile.get("evidence", {})
            reasons = profile.get("blocked_reasons", [])
            trusted_exhausted = (
                bool(reasons)
                and all(reason == "provider quota window exhausted; refresh status" for reason in reasons)
                and profile.get("authorized") is True
                and profile.get("image_capability") is True
                and profile.get("entitlement") == "verified"
                and evidence.get("source") in {"host_tool", "provider_status", "user_confirmed", "authorized_smoke_test"}
                and any(float(window.get("used_percent", 0)) >= 100
                        for window in profile.get("limits", {}).get("quota_windows", [])))
            if profile.get("eligible") is not True and not trusted_exhausted:
                continue
            if (not profile.get("limits") or not evidence.get("checked_at")
                    or evidence.get("checked_at", 0) > self.clock()
                    or evidence.get("expires_at", 0) <= self.clock()
                    or (profile.get("status_expires_at") is not None
                        and profile["status_expires_at"] <= self.clock())
                    or profile.get("status_checked_at", 0) > self.clock()):
                continue
            group = profile.get("quota_group", profile["id"])
            groups.setdefault(group, []).append(profile)
            limits = profile["limits"]
            if int(limits["max_parallel"]) < 1 or int(limits.get("initial_parallel", 1)) < 1:
                raise ValueError("Verified and initial concurrency must be positive")
            for key in ("requests_per_minute", "requests_per_day", "remaining_requests"):
                if limits.get(key) is not None and int(limits[key]) < 0:
                    raise ValueError("Request limits cannot be negative")
            _decimal(profile.get("cost", {}).get("per_request", 0))
        self.db.execute("BEGIN IMMEDIATE")
        try:
            for group, profiles in groups.items():
                currencies = {p.get("cost", {}).get("currency", "USD") for p in profiles}
                if len(currencies) != 1:
                    raise ValueError("Conflicting currencies within a shared quota group")
                currency = next(iter(currencies))
                cap = min(int(p["limits"]["max_parallel"]) for p in profiles)
                initial = min(cap, *(int(p["limits"].get("initial_parallel", 1)) for p in profiles))
                checked = min(float(p.get("status_checked_at", p["evidence"]["checked_at"])) for p in profiles)
                def minimum(key: str):
                    values = [int(p["limits"][key]) for p in profiles
                              if p["limits"].get(key) is not None]
                    return min(values) if values else None
                row = self.db.execute("SELECT * FROM quota_groups WHERE group_id=?", (group,)).fetchone()
                if row is not None and row["currency"] != currency:
                    raise ValueError(f"Currency changed for quota group '{group}'; reconcile the existing ledger before changing budget currency")
                if row is None:
                    self.db.execute("""INSERT INTO quota_groups
                        (group_id,currency,max_parallel,parallel_limit,rpm,rpd,limits_checked)
                        VALUES (?,?,?,?,?,?,?)""", (group, currency, cap, initial,
                                                   minimum("requests_per_minute"),
                                                   minimum("requests_per_day"), checked))
                elif checked >= row["limits_checked"]:
                    self.db.execute("""UPDATE quota_groups SET max_parallel=?,
                        parallel_limit=MIN(parallel_limit,?),rpm=?,rpd=?,limits_checked=?
                        WHERE group_id=?""", (cap, cap, minimum("requests_per_minute"),
                                               minimum("requests_per_day"), checked, group))
                if row is not None and row["blocked_checked"] is not None and checked > row["blocked_checked"]:
                    self.db.execute("UPDATE quota_groups SET blocked_reason=NULL,blocked_checked=NULL WHERE group_id=?", (group,))
                windows = [(float(p.get("status_checked_at", p["evidence"]["checked_at"])), window)
                           for p in profiles for window in p["limits"].get("quota_windows", [])]
                if windows:
                    newest = max(stamp for stamp, _ in windows)
                    if any(float(window["used_percent"]) >= 100 for stamp, window in windows if stamp == newest):
                        current = self.db.execute("SELECT blocked_checked,limits_checked FROM quota_groups WHERE group_id=?", (group,)).fetchone()
                        if newest >= current[1] and (current[0] is None or newest >= current[0]):
                            self.db.execute("UPDATE quota_groups SET blocked_reason='quota_window_exhausted',blocked_checked=? WHERE group_id=?", (newest, group))
                for source, field, stamp_field in (("remaining_requests", "remaining", "balance_checked"),
                                                   ("budget_remaining", "budget", "budget_checked")):
                    candidates = [p for p in profiles if p.get("eligible") is True
                                  and p.get("limits" if field == "remaining" else "cost", {}).get(source) is not None]
                    if not candidates:
                        continue
                    section = "limits" if field == "remaining" else "cost"
                    stamp_key = "remaining_checked_at" if field == "remaining" else "budget_checked_at"
                    def snapshot_stamp(p):
                        return float(p[section].get(stamp_key, p["evidence"]["checked_at"]))
                    stamp = max(snapshot_stamp(p) for p in candidates)
                    candidates = [p for p in candidates if snapshot_stamp(p) == stamp]
                    current = self.db.execute("SELECT * FROM quota_groups WHERE group_id=?", (group,)).fetchone()
                    if current[stamp_field] is not None and stamp < current[stamp_field]:
                        continue
                    same_snapshot = stamp == current[stamp_field]
                    if field == "remaining":
                        balance = min(int(p["limits"][source]) for p in candidates)
                        used = self.db.execute("SELECT COUNT(*) FROM reservations WHERE group_id=? AND (created_at>=? OR status IN ('in_flight','ambiguous'))", (group, stamp)).fetchone()[0]
                        remaining = max(0, balance-used)
                        if same_snapshot and current["remaining"] is not None:
                            remaining = min(remaining, current["remaining"])
                        self.db.execute("UPDATE quota_groups SET remaining=?,balance_checked=?,reset_at=? WHERE group_id=?",
                                        (remaining, stamp, candidates[0]["limits"].get("reset_at"), group))
                    else:
                        budget = min(_decimal(p["cost"][source]) for p in candidates)
                        spent = sum((_decimal(r[0]) for r in self.db.execute(
                            "SELECT cost FROM reservations WHERE group_id=? AND (created_at>=? OR status IN ('in_flight','ambiguous'))", (group, stamp))), Decimal(0))
                        remaining_budget = max(Decimal(0), budget-spent)
                        if same_snapshot and current["budget"] is not None:
                            remaining_budget = min(remaining_budget, _decimal(current["budget"]))
                        self.db.execute("UPDATE quota_groups SET budget=?,budget_checked=? WHERE group_id=?",
                                        (str(remaining_budget), stamp, group))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    @staticmethod
    def _validate_jobs(jobs: list[dict]) -> None:
        ids = {job["id"] for job in jobs}
        if len(ids) != len(jobs):
            raise ValueError("Duplicate job IDs")
        images = [str(Path(job["image"]).resolve()) for job in jobs if job.get("image")]
        if len(set(images)) != len(images):
            raise ValueError("Conflicting output paths")
        edges = {job["id"]: set(job.get("depends_on", [])) for job in jobs}
        if any(not dependencies <= ids for dependencies in edges.values()):
            raise ValueError("Unknown dependency")
        visited, visiting = set(), set()
        def visit(job_id):
            if job_id in visiting:
                raise ValueError("Dependency cycle")
            if job_id in visited:
                return
            visiting.add(job_id)
            for dependency in edges[job_id]:
                visit(dependency)
            visiting.remove(job_id)
            visited.add(job_id)
        for job_id in edges:
            visit(job_id)

    def _expire_leases(self, now: float) -> None:
        for row in self.db.execute("SELECT * FROM reservations WHERE status='in_flight' AND expires_at<=?", (now,)).fetchall():
            result = json.dumps({"status": "ambiguous", "reason": "lease_expired", "token": row["token"]})
            self.db.execute("UPDATE reservations SET status='ambiguous',outcome=? WHERE token=?", (result, row["token"]))
            self.db.execute("UPDATE jobs SET status='ambiguous',result=? WHERE token=?", (result, row["token"]))

    @classmethod
    def fingerprints(cls, jobs: list[dict]) -> dict[str, str]:
        """Include dependency inputs so changed anchors invalidate their children."""
        cls._validate_jobs(jobs)
        by_id, computed = {job["id"]: job for job in jobs}, {}
        def fingerprint(job_id):
            if job_id not in computed:
                job = by_id[job_id]
                computed[job_id] = _hash({
                    "job": {key: value for key, value in job.items() if key not in REVIEW_FIELDS},
                    "dependencies": {dep: fingerprint(dep) for dep in job.get("depends_on", [])},
                })
            return computed[job_id]
        for job_id in by_id:
            fingerprint(job_id)
        return computed

    def _resume_blocker(self, row) -> str | None:
        profile = self.profiles.get(row["route_id"])
        if not profile or _profile_hash(profile) != row["profile_hash"]:
            return "profile_identity_changed"
        if row["image"] and not Path(row["image"]).is_file():
            return "completed_output_missing"
        if row["image"]:
            expected = json.loads(row["result"] or "{}").get("sha256")
            if expected is None:
                return "completed_output_unverified"
            if self._image_digest(Path(row["image"])) != expected:
                return "completed_output_changed"
        return None

    def _image_digest(self, path: Path) -> str:
        stat = path.stat()
        key = (str(path), stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        if key not in self._digest_cache:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(512 * 1024), b""):
                    digest.update(block)
            self._digest_cache[key] = digest.hexdigest()
        return self._digest_cache[key]

    def validate_record(self, *, run_id: str, job_id: str, token: str,
                        jobs: list[dict] | None = None) -> dict:
        """Read-only validation to perform BEFORE importing a host tool output."""
        row = self.db.execute("SELECT * FROM jobs WHERE run_id=? AND job_id=? AND token=?", (run_id, job_id, token)).fetchone()
        if row is None:
            raise ValueError("Unknown reservation token or job")
        if jobs is not None and self.fingerprints(jobs).get(job_id) != row["fingerprint"]:
            raise ValueError("Storyboard changed since the reservation")
        profile = self.profiles.get(row["route_id"])
        if not profile or _profile_hash(profile) != row["profile_hash"]:
            raise ValueError("Provider identity changed since the reservation")
        return {key: row[key] for key in ("image", "status", "fingerprint", "route_id", "token")} | {
            "result": json.loads(row["result"] or "{}")}

    def _route_blocker(self, profile: dict, now: float) -> tuple[str | None, float | None]:
        if not profile.get("eligible", False):
            return "route_ineligible", None
        if float(profile["evidence"]["expires_at"]) <= now:
            return "evidence_expired", None
        if profile.get("status_expires_at") is not None and float(profile["status_expires_at"]) <= now:
            return "provider_status_expired", None
        if float(profile.get("status_checked_at", 0)) > now:
            return "provider_status_from_future", None
        if float(profile["evidence"]["checked_at"]) > now:
            return "evidence_from_future", None
        group_id = profile.get("quota_group", profile["id"])
        group = self.db.execute("SELECT * FROM quota_groups WHERE group_id=?", (group_id,)).fetchone()
        if group["blocked_reason"]:
            return group["blocked_reason"], None
        if group["cooldown_until"] > now:
            return "provider_cooldown", group["cooldown_until"]
        if group["remaining"] is not None and group["remaining"] < 1:
            return "quota_snapshot_exhausted", None
        cost = _decimal(profile.get("cost", {}).get("per_request", 0))
        if group["budget"] is not None and _decimal(group["budget"]) < cost:
            return "budget_exhausted", None
        active = self.db.execute("SELECT COUNT(*) FROM reservations WHERE status IN ('in_flight','ambiguous') AND group_id=?", (group_id,)).fetchone()[0]
        if active >= group["parallel_limit"]:
            return "shared_group_at_capacity", None
        route_active = self.db.execute("SELECT COUNT(*) FROM reservations WHERE status IN ('in_flight','ambiguous') AND route_id=?", (profile["id"],)).fetchone()[0]
        if route_active >= int(profile["limits"]["max_parallel"]):
            return "route_at_capacity", None
        for field, window in (("rpm", 60), ("rpd", 86400)):
            if group[field] is None:
                continue
            rows = self.db.execute("SELECT created_at FROM reservations WHERE group_id=? AND created_at>? ORDER BY created_at", (group_id, now-window)).fetchall()
            if len(rows) >= group[field]:
                return ("requests_per_minute" if field == "rpm" else "requests_per_day"), (rows[0][0]+window if rows and group[field] > 0 else None)
        return None, None

    def claim(self, jobs: list[dict], *, run_id: str) -> dict:
        """Atomically claim only immediately executable jobs; never wait for slots."""
        self._validate_jobs(jobs)
        self._digest_cache.clear()
        now = float(self.clock())
        leases, blockers, results = [], [], []
        hashes = self.fingerprints(jobs)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self._expire_leases(now)
            states = {}
            for job in jobs:
                row = self.db.execute("SELECT * FROM jobs WHERE run_id=? AND job_id=? AND fingerprint=?", (run_id, job["id"], hashes[job["id"]])).fetchone()
                if (row and row["status"] == "review_required" and job.get("reviewed") is True
                        and job.get("review_token") == row["token"]):
                    result = json.loads(row["result"] or "{}")
                    result.update(status="success", reviewed=True)
                    self.db.execute("UPDATE jobs SET status='success',result=? WHERE run_id=? AND job_id=? AND fingerprint=?", (json.dumps(result), run_id, job["id"], hashes[job["id"]]))
                    row = self.db.execute("SELECT * FROM jobs WHERE run_id=? AND job_id=? AND fingerprint=?", (run_id, job["id"], hashes[job["id"]])).fetchone()
                states[job["id"]] = row
            # Dispatch constrained jobs first so a flexible scene does not take
            # the only reference-capable route while another route sits idle.
            def route_options(job):
                return sum(bool(p.get("eligible"))
                           and (job.get("allowed_routes") is None or p["id"] in job["allowed_routes"])
                           and (not job.get("requires_references") or p.get("supports_references"))
                           for p in self.profiles.values())
            for job in sorted(jobs, key=route_options):
                job_id, fingerprint = job["id"], hashes[job["id"]]
                row = states[job_id]
                status = row["status"] if row else "pending"
                if row and status in {"success", "review_required", "ambiguous", "failed", "in_flight"}:
                    result = json.loads(row["result"] or "{}")
                    result.update(id=job_id, status=status, provider=row["route_id"], attempts=row["attempts"])
                    if status in {"success", "review_required"}:
                        reason = self._resume_blocker(row)
                        if reason:
                            result.update(status="pending", reason=reason)
                            blockers.append({"job_id": job_id, "reason": reason})
                        elif status == "review_required":
                            reason = "awaiting_review_token" if job.get("reviewed") is True else "awaiting_review"
                            result["reason"] = reason
                            blockers.append({"job_id": job_id, "reason": reason})
                    results.append(result)
                    continue
                if row and row["attempts"] >= self.max_attempts:
                    self.db.execute("UPDATE jobs SET status='failed' WHERE run_id=? AND job_id=? AND fingerprint=?", (run_id, job_id, fingerprint))
                    results.append({"id": job_id, "status": "failed", "reason": "attempts_exhausted", "attempts": row["attempts"]})
                    continue
                blocked_dependencies = []
                for dependency in job.get("depends_on", []):
                    parent = states[dependency]
                    if not parent or parent["status"] != "success" or self._resume_blocker(parent):
                        blocked_dependencies.append(dependency)
                if blocked_dependencies:
                    blockers.append({"job_id": job_id, "reason": "dependencies", "dependencies": blocked_dependencies})
                    results.append({"id": job_id, "status": "pending", "reason": "dependencies"})
                    continue
                if row and row["next_attempt_at"] > now:
                    blockers.append({"job_id": job_id, "reason": "retry_backoff", "retry_at": row["next_attempt_at"]})
                    results.append({"id": job_id, "status": "pending", "reason": "retry_backoff"})
                    continue
                if job.get("image") and Path(job["image"]).exists():
                    blockers.append({"job_id": job_id, "reason": "output_exists"})
                    results.append({"id": job_id, "status": "pending", "reason": "output_exists"})
                    continue
                image = str(Path(job["image"]).resolve()) if job.get("image") else None
                if image and self.db.execute("SELECT 1 FROM jobs WHERE image=? AND status IN ('in_flight','ambiguous','success','review_required') LIMIT 1", (image,)).fetchone():
                    blockers.append({"job_id": job_id, "reason": "output_already_reserved"})
                    results.append({"id": job_id, "status": "pending", "reason": "output_already_reserved"})
                    continue
                active = self.db.execute("SELECT COUNT(*) FROM reservations WHERE status IN ('in_flight','ambiguous')").fetchone()[0]
                if active >= self.max_in_flight:
                    blockers.append({"job_id": job_id, "reason": "global_capacity"})
                    results.append({"id": job_id, "status": "pending", "reason": "global_capacity"})
                    continue
                affinity = None
                if job.get("affinity_group"):
                    affinity = self.db.execute("SELECT route_id FROM affinity WHERE run_id=? AND affinity_group=?", (run_id, job["affinity_group"])).fetchone()
                candidates, reasons = [], []
                for profile in self.profiles.values():
                    if job.get("allowed_routes") is not None and profile["id"] not in job["allowed_routes"]:
                        continue
                    if affinity and profile["id"] != affinity[0]:
                        continue
                    if job.get("requires_references") and not profile.get("supports_references", False):
                        continue
                    reason, retry_at = self._route_blocker(profile, now)
                    if reason:
                        reasons.append({"route_id": profile["id"], "reason": reason, "retry_at": retry_at})
                    else:
                        count = self.db.execute("SELECT COUNT(*) FROM reservations WHERE route_id=? AND status IN ('in_flight','ambiguous')", (profile["id"],)).fetchone()[0]
                        candidates.append((count / int(profile["limits"]["max_parallel"]), profile["id"], profile))
                if not candidates:
                    blocker = {"job_id": job_id, "reason": "no_ready_route", "routes": reasons}
                    retry_times = [r["retry_at"] for r in reasons if r["retry_at"] is not None]
                    if retry_times:
                        blocker["retry_at"] = min(retry_times)
                    blockers.append(blocker)
                    results.append({"id": job_id, "status": "pending", "reason": "no_ready_route"})
                    continue
                profile = min(candidates, key=lambda item: (item[0], item[1]))[2]
                group_id = profile.get("quota_group", profile["id"])
                token = uuid.uuid4().hex
                attempt = (row["attempts"] if row else 0) + 1
                expires = now + max(1, float(profile.get("timeout_seconds", 600)))
                cost = _decimal(profile.get("cost", {}).get("per_request", 0))
                self.db.execute("""INSERT INTO reservations
                    (token,run_id,job_id,fingerprint,route_id,group_id,created_at,expires_at,cost,status)
                    VALUES (?,?,?,?,?,?,?,?,?,'in_flight')""", (token, run_id, job_id, fingerprint, profile["id"], group_id, now, expires, str(cost)))
                group = self.db.execute("SELECT * FROM quota_groups WHERE group_id=?", (group_id,)).fetchone()
                self.db.execute("UPDATE quota_groups SET remaining=?,budget=? WHERE group_id=?", (
                    group["remaining"]-1 if group["remaining"] is not None else None,
                    str(_decimal(group["budget"])-cost) if group["budget"] is not None else None, group_id))
                self.db.execute("""INSERT INTO jobs
                    (run_id,job_id,fingerprint,status,route_id,profile_hash,token,attempts,review_required,image)
                    VALUES (?,?,?,'in_flight',?,?,?,?,?,?) ON CONFLICT(run_id,job_id,fingerprint)
                    DO UPDATE SET status='in_flight',route_id=excluded.route_id,
                    profile_hash=excluded.profile_hash,token=excluded.token,attempts=excluded.attempts,
                    result=NULL,next_attempt_at=0""", (run_id, job_id, fingerprint, profile["id"], _profile_hash(profile), token, attempt, int(bool(job.get("review_required"))), image))
                if job.get("affinity_group"):
                    self.db.execute("INSERT OR IGNORE INTO affinity VALUES (?,?,?)", (run_id, job["affinity_group"], profile["id"]))
                leases.append({"job_id": job_id, "route_id": profile["id"], "attempt": attempt, "token": token, "lease_expires_at": expires})
                results.append({"id": job_id, "status": "in_flight", "provider": profile["id"], "attempts": attempt})
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        retry_times = [b["retry_at"] for b in blockers if b.get("retry_at") is not None]
        return {"leases": leases, "results": results, "blockers": blockers,
                "next_retry_at": min(retry_times) if retry_times else None,
                "completed": sum(r["status"] == "success" for r in results), "total_assets": len(jobs)}

    def record(self, *, run_id: str, job_id: str, token: str, outcome: dict) -> dict:
        """Record an idempotent result; unknown/timeout results must stay ambiguous."""
        now = float(self.clock())
        allowed = {"success", "review_required", "rate_limited", "transient_error", "quota_exhausted", "unauthorized", "permanent_error", "ambiguous"}
        raw_status = outcome.get("status", "ambiguous")
        if raw_status not in allowed:
            raw_status = "ambiguous"
        self.db.execute("BEGIN IMMEDIATE")
        try:
            reservation = self.db.execute("SELECT * FROM reservations WHERE token=? AND run_id=? AND job_id=?", (token, run_id, job_id)).fetchone()
            if reservation is None:
                raise ValueError("Unknown reservation token or job")
            row = self.db.execute("SELECT * FROM jobs WHERE token=?", (token,)).fetchone()
            if row is None:
                raise ValueError("Reservation no longer owns this job")
            if reservation["status"] not in {"in_flight", "ambiguous"}:
                self.db.commit()
                return json.loads(row["result"] or "{}")
            group = self.db.execute("SELECT * FROM quota_groups WHERE group_id=?", (reservation["group_id"],)).fetchone()
            result = {key: value for key, value in outcome.items() if key in {"output", "reason", "error", "retry_after"}}
            if raw_status in {"success", "review_required"} and row["image"] and Path(row["image"]).is_file():
                result["sha256"] = self._image_digest(Path(row["image"]))
            status, next_attempt = raw_status, 0
            if raw_status == "success":
                status = "review_required" if row["review_required"] else "success"
                clean = group["clean_successes"] + int(now >= group["cooldown_until"])
                parallel = group["parallel_limit"]
                if clean >= max(3, parallel) and parallel < group["max_parallel"]:
                    parallel += 1
                    clean = 0
                self.db.execute("UPDATE quota_groups SET parallel_limit=?,clean_successes=? WHERE group_id=?", (parallel, clean, reservation["group_id"]))
            elif raw_status in {"rate_limited", "transient_error"}:
                delay = min(60, 2 ** min(row["attempts"], 8)) + random.uniform(0, 1)
                try:
                    retry_after = max(0, float(outcome.get("retry_after", 0)))
                    if not (retry_after < float("inf")):
                        raise ValueError("Nonfinite Retry-After")
                except (TypeError, ValueError, OverflowError):
                    retry_after = 60
                next_attempt = now + max(delay, retry_after)
                status = "pending" if row["attempts"] < self.max_attempts else "failed"
                if raw_status == "rate_limited":
                    self.db.execute("UPDATE quota_groups SET parallel_limit=MAX(1,parallel_limit/2),clean_successes=0,cooldown_until=MAX(cooldown_until,?) WHERE group_id=?", (next_attempt, reservation["group_id"]))
            elif raw_status == "quota_exhausted":
                self.db.execute("UPDATE quota_groups SET blocked_reason='quota_exhausted',blocked_checked=? WHERE group_id=?", (group["limits_checked"], reservation["group_id"]))
                status = "pending" if row["attempts"] < self.max_attempts else "failed"
            elif raw_status == "unauthorized":
                self.db.execute("UPDATE quota_groups SET blocked_reason='unauthorized',blocked_checked=? WHERE group_id=?", (group["limits_checked"], reservation["group_id"]))
                status = "pending" if row["attempts"] < self.max_attempts else "failed"
            elif raw_status == "permanent_error":
                status = "failed"
            result.update(id=job_id, status=status, outcome=raw_status,
                          provider=reservation["route_id"], attempts=row["attempts"], token=token)
            self.db.execute("UPDATE reservations SET status=?,outcome=? WHERE token=?", (raw_status, json.dumps(result), token))
            self.db.execute("UPDATE jobs SET status=?,next_attempt_at=?,result=? WHERE token=?", (status, next_attempt, json.dumps(result), token))
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def run(self, jobs: list[dict], generate: Callable, *, run_id: str) -> dict:
        """Keep available routes busy, bound queue waiting, and drain started calls."""
        self._validate_jobs(jobs)
        by_id = {job["id"]: job for job in jobs}
        idle_wait = 0.0
        inflight: dict[concurrent.futures.Future, dict] = {}
        summary = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_in_flight) as executor:
            while True:
                # Results are committed individually before another dispatch.
                done = [future for future in inflight if future.done()]
                for future in done:
                    lease = inflight.pop(future)
                    try:
                        outcome = future.result()
                        if not isinstance(outcome, dict):
                            outcome = {"status": "ambiguous", "reason": "invalid_adapter_result"}
                    except BaseException:
                        outcome = {"status": "ambiguous", "reason": "adapter_exception"}
                    self.record(run_id=run_id, job_id=lease["job_id"], token=lease["token"], outcome=outcome)
                summary = self.claim(jobs, run_id=run_id)
                for lease in summary["leases"]:
                    future = executor.submit(generate, by_id[lease["job_id"]], self.profiles[lease["route_id"]], lease["attempt"])
                    inflight[future] = lease
                if inflight:
                    concurrent.futures.wait(inflight, timeout=0.05, return_when=concurrent.futures.FIRST_COMPLETED)
                    continue
                if summary["leases"]:
                    continue
                retry_at = summary["next_retry_at"]
                remaining_wait = self.max_wait_seconds - idle_wait
                delay = max(0.001, retry_at-float(self.clock())) if retry_at is not None else None
                if delay is None or delay > remaining_wait:
                    break
                step = min(1, delay)
                self.sleeper(step)
                idle_wait += step
        # Read-only terminal snapshot: never claim work after the loop ends.
        final = self.snapshot(jobs, run_id=run_id)
        final["blockers"] = summary["blockers"] if summary else []
        final["next_retry_at"] = summary["next_retry_at"] if summary else None
        return final

    def snapshot(self, jobs: list[dict], *, run_id: str) -> dict:
        """Return journal states without creating reservations."""
        results = []
        self._digest_cache.clear()
        hashes = self.fingerprints(jobs)
        for job in jobs:
            row = self.db.execute("SELECT * FROM jobs WHERE run_id=? AND job_id=? AND fingerprint=?", (run_id, job["id"], hashes[job["id"]])).fetchone()
            result = json.loads(row["result"] or "{}") if row else {}
            result.update(id=job["id"], status=row["status"] if row else "pending")
            if row:
                result.update(provider=row["route_id"], attempts=row["attempts"])
                if row["status"] in {"success", "review_required"}:
                    reason = self._resume_blocker(row)
                    if reason:
                        result.update(status="pending", reason=reason)
            results.append(result)
        return {"results": results, "completed": sum(r["status"] == "success" for r in results),
                "total_assets": len(jobs)}
