"""Offline scheduler tests: accounts, resumability, dependencies, and dispatch."""

import copy
from decimal import Decimal
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "dual-image-pipeline" / "scripts"))
from scheduler import Scheduler


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def profile(route="agy", group=None, slots=2, **limits):
    return {"id": route, "quota_group": group or route, "eligible": True,
            "authorized": True, "image_capability": True, "entitlement": "verified",
            "kind": "host_tool", "supports_references": True,
            "limits": {"max_parallel": slots, "initial_parallel": slots, **limits},
            "cost": {"per_request": "0"},
            "evidence": {"checked_at": 999, "expires_at": 10000, "source": "provider_status"}}


def _process_claim(state, provider, jobs, pipe):
    broker = Scheduler([provider], Path(state), clock=lambda: 1000.0)
    try:
        pipe.send("ready")
        pipe.recv()
        pipe.send(broker.claim(jobs, run_id="run")["leases"])
    finally:
        broker.close()
        pipe.close()


class ImageSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.clock = FakeClock()

    def broker(self, profiles=None, **kwargs):
        broker = Scheduler(profiles or [profile()], self.path / "state.sqlite",
                           clock=self.clock, sleeper=self.clock.sleep, **kwargs)
        self.addCleanup(broker.close)
        return broker

    def jobs(self, count, **extras):
        return [{"id": str(index), "prompt": "scene " + str(index),
                 "image": str(self.path / (str(index) + ".png")), **extras}
                for index in range(count)]

    def finish(self, broker, leases, status="success", **extra):
        if status in {"success", "review_required"}:
            for lease in leases:
                record = broker.validate_record(run_id="run", job_id=lease["job_id"], token=lease["token"])
                if record["image"]:
                    Path(record["image"]).write_bytes(b"test image")
        return [broker.record(run_id="run", job_id=lease["job_id"], token=lease["token"],
                              outcome={"status": status, **extra}) for lease in leases]

    def test_shared_account_and_global_caps(self):
        broker = self.broker([profile("a", "shared", 3), profile("b", "shared", 3),
                              profile("c", "other", 3)], max_in_flight=4)
        claimed = broker.claim(self.jobs(8), run_id="run")
        self.assertEqual(len(claimed["leases"]), 4)
        shared = sum(lease["route_id"] in {"a", "b"} for lease in claimed["leases"])
        self.assertLessEqual(shared, 3)
        other = self.broker([profile("a", "shared", 3)], max_in_flight=4)
        self.assertEqual(other.claim(self.jobs(8), run_id="run")["leases"], [])

    def test_two_connections_cannot_double_claim_job_or_balance(self):
        p = profile(slots=4, remaining_requests=1)
        first, second = self.broker([p]), self.broker([p])
        one = first.claim(self.jobs(3), run_id="run")
        two = second.claim(self.jobs(3), run_id="run")
        self.assertEqual(len(one["leases"]), 1)
        self.assertEqual(two["leases"], [])
        self.finish(first, one["leases"], "transient_error")
        self.clock.sleep(5)
        self.assertEqual(second.claim(self.jobs(3), run_id="run")["leases"], [])

    def test_budget_is_shared_exact_and_failure_is_charged(self):
        a, b = profile("a", "same"), profile("b", "same")
        a["cost"] = {"per_request": "0.10", "budget_remaining": "0.30"}
        b["cost"] = {"per_request": "0.20", "budget_remaining": "0.30"}
        broker = self.broker([a, b])
        claimed = broker.claim(self.jobs(4), run_id="run")
        self.assertEqual(len(claimed["leases"]), 2)
        self.finish(broker, claimed["leases"], "permanent_error")
        self.assertEqual(broker.claim(self.jobs(5), run_id="run")["leases"], [])
        self.assertEqual(broker.db.execute("SELECT budget FROM quota_groups").fetchone()[0], "0.00")

    def test_only_newer_snapshot_replenishes_numeric_balance(self):
        p = profile(remaining_requests=2)
        first = self.broker([p])
        self.finish(first, first.claim(self.jobs(2), run_id="run")["leases"])
        for checked in (998, 999):
            stale = copy.deepcopy(p)
            stale["limits"]["remaining_requests"] = 100
            stale["evidence"]["checked_at"] = checked
            reloaded = self.broker([stale])
            self.assertEqual(reloaded.claim(self.jobs(3), run_id="run")["leases"], [])
        self.clock.sleep(10)
        p["evidence"]["checked_at"] = 1009
        newest = self.broker([p])
        self.assertEqual(len(newest.claim(self.jobs(3), run_id="run")["leases"]), 1)

    def test_numeric_balance_does_not_refill_at_reset_time(self):
        broker = self.broker([profile(remaining_requests=0, reset_at=1001)])
        self.clock.sleep(100)
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])

    def test_percentage_quota_blocks_until_new_snapshot(self):
        p = profile(quota_windows=[{"used_percent": 100, "resets_at": 1001, "window_minutes": 60}])
        broker = self.broker([p])
        self.clock.sleep(20)
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])
        p["evidence"]["checked_at"] = 1019
        p["limits"]["quota_windows"][0]["used_percent"] = 0
        refreshed = self.broker([p])
        self.assertEqual(len(refreshed.claim(self.jobs(1), run_id="run")["leases"]), 1)

    def test_rpm_and_daily_limits_count_failed_attempts(self):
        broker = self.broker([profile(requests_per_minute=1, requests_per_day=2)])
        first = broker.claim(self.jobs(4), run_id="run")
        self.finish(broker, first["leases"], "permanent_error")
        self.assertEqual(broker.claim(self.jobs(4), run_id="run")["next_retry_at"], 1060)
        self.clock.sleep(60)
        second = broker.claim(self.jobs(4), run_id="run")
        self.assertEqual(len(second["leases"]), 1)
        self.finish(broker, second["leases"], "permanent_error")
        self.clock.sleep(60)
        self.assertEqual(broker.claim(self.jobs(4), run_id="run")["leases"], [])

    def test_retry_after_reduces_group_parallelism_then_recovers_gradually(self):
        broker = self.broker([profile(slots=4)], max_attempts=3)
        claimed = broker.claim(self.jobs(4), run_id="run")
        self.finish(broker, claimed["leases"][:1], "rate_limited", retry_after=30)
        self.finish(broker, claimed["leases"][1:3])
        group = broker.db.execute("SELECT * FROM quota_groups").fetchone()
        self.assertEqual(group["parallel_limit"], 2)
        self.assertEqual(broker.claim(self.jobs(5), run_id="run")["leases"], [])
        self.finish(broker, claimed["leases"][3:])
        self.assertEqual(broker.db.execute("SELECT parallel_limit FROM quota_groups").fetchone()[0], 2)
        self.clock.sleep(29)
        self.assertEqual(broker.claim(self.jobs(5), run_id="run")["leases"], [])
        self.clock.sleep(1)
        next_batch = broker.claim(self.jobs(6), run_id="run")["leases"]
        self.assertEqual(len(next_batch), 2)
        self.finish(broker, next_batch)
        self.finish(broker, broker.claim(self.jobs(7), run_id="run")["leases"])
        self.assertEqual(broker.db.execute("SELECT parallel_limit FROM quota_groups").fetchone()[0], 3)

    def test_dependency_requires_review_and_affinity_stays_pinned(self):
        jobs = self.jobs(3, affinity_group="person", requires_references=True)
        jobs[0]["review_required"] = True
        jobs[1]["depends_on"] = ["0"]
        jobs[2]["depends_on"] = ["1"]
        broker = self.broker([profile("a"), profile("b")])
        first = broker.claim(jobs, run_id="run")
        self.assertEqual([x["job_id"] for x in first["leases"]], ["0"])
        self.finish(broker, first["leases"])
        self.assertEqual(broker.claim(jobs, run_id="run")["leases"], [])
        jobs[0]["review_token"] = first["leases"][0]["token"]
        jobs[0]["reviewed"] = True
        second = broker.claim(jobs, run_id="run")
        self.assertEqual([x["job_id"] for x in second["leases"]], ["1"])
        self.assertEqual(second["leases"][0]["route_id"], first["leases"][0]["route_id"])

    def test_reference_and_allowed_route_filter(self):
        a, b = profile("a"), profile("b")
        a["supports_references"] = False
        broker = self.broker([a, b])
        jobs = self.jobs(1, requires_references=True, allowed_routes=["a"])
        self.assertEqual(broker.claim(jobs, run_id="run")["leases"], [])

    def test_expired_lease_is_ambiguous_and_late_original_result_resolves(self):
        p = profile()
        p["timeout_seconds"] = 10
        broker = self.broker([p])
        jobs = self.jobs(1)
        lease = broker.claim(jobs, run_id="run")["leases"][0]
        another_process = self.broker([p])
        self.assertEqual(another_process.claim(jobs, run_id="run")["results"][0]["status"], "in_flight")
        self.clock.sleep(10)
        expired = another_process.claim(jobs, run_id="run")
        self.assertEqual(expired["leases"], [])
        self.assertEqual(expired["results"][0]["status"], "ambiguous")
        self.finish(broker, [lease])
        self.assertEqual(another_process.claim(jobs, run_id="run")["completed"], 1)

    def test_resume_and_changed_fingerprint_do_not_duplicate_or_overwrite(self):
        broker = self.broker()
        jobs = self.jobs(1)
        self.finish(broker, broker.claim(jobs, run_id="run")["leases"])
        self.assertEqual(broker.claim(jobs, run_id="run")["completed"], 1)
        jobs[0]["prompt"] = "different"
        changed = broker.claim(jobs, run_id="run")
        self.assertEqual(changed["leases"], [])
        self.assertEqual(changed["blockers"][0]["reason"], "output_exists")

    def test_fingerprint_change_blocks_dependent_reuse(self):
        p = profile()
        broker = self.broker([p])
        jobs = self.jobs(2)
        jobs[1]["depends_on"] = ["0"]
        self.finish(broker, broker.claim(jobs, run_id="run")["leases"])
        p["model"] = "different"
        reconfigured = self.broker([p])
        state = reconfigured.claim(jobs, run_id="run")
        self.assertEqual(state["leases"], [])
        self.assertEqual(state["completed"], 0)

    def test_expired_evidence_stops_new_calls(self):
        p = profile()
        p["evidence"]["expires_at"] = 1001
        broker = self.broker([p])
        self.clock.sleep(1)
        state = broker.claim(self.jobs(1), run_id="run")
        self.assertEqual(state["leases"], [])
        self.assertEqual(state["blockers"][0]["routes"][0]["reason"], "evidence_expired")

    def test_unknown_exception_is_ambiguous_and_never_retried(self):
        broker = self.broker()
        def broken(*args):
            raise TimeoutError("unknown outcome")
        state = broker.run(self.jobs(1), broken, run_id="run")
        self.assertEqual(state["results"][0]["status"], "ambiguous")
        self.assertEqual(state["results"][0]["attempts"], 1)

    def test_attempts_and_wait_budget_are_bounded(self):
        broker = self.broker(max_attempts=2, max_wait_seconds=20)
        state = broker.run(self.jobs(1), lambda *args: {"status": "transient_error"}, run_id="run")
        self.assertEqual(state["results"][0]["attempts"], 2)
        self.assertEqual(state["results"][0]["status"], "failed")
        jobs = [{"id": "other", "prompt": "other"}]
        state = broker.run(jobs, lambda *args: {"status": "rate_limited", "retry_after": 100}, run_id="run")
        self.assertEqual(state["results"][0]["status"], "pending")
        self.assertLess(self.clock(), 1020)

    def test_slow_route_does_not_block_fast_route_dispatch(self):
        now = time.time()
        profiles = [profile("a", slots=1), profile("b", slots=1)]
        for p in profiles:
            p["evidence"] = {"checked_at": now-1, "expires_at": now+100}
        broker = Scheduler(profiles, self.path / "live-clock.sqlite", max_in_flight=2)
        self.addCleanup(broker.close)
        fast_finished = threading.Event()
        fast_calls = []
        slow_saw_fast = []
        def generate(job, route, attempt):
            if route["id"] == "a":
                slow_saw_fast.append(fast_finished.wait(2))
            else:
                fast_calls.append(job["id"])
                if len(fast_calls) >= 3:
                    fast_finished.set()
            Path(job["image"]).write_bytes(b"test image")
            return {"status": "success"}
        result = broker.run(self.jobs(6), generate, run_id="run")
        self.assertEqual(result["completed"], 6)
        self.assertTrue(all(slow_saw_fast))
        self.assertGreaterEqual(len(fast_calls), 3)

    def test_dependency_cycles_and_duplicate_paths_rejected(self):
        broker = self.broker()
        jobs = self.jobs(2)
        jobs[0]["depends_on"], jobs[1]["depends_on"] = ["1"], ["0"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            broker.claim(jobs, run_id="run")
        jobs = self.jobs(2)
        jobs[1]["image"] = jobs[0]["image"]
        with self.assertRaisesRegex(ValueError, "output"):
            broker.claim(jobs, run_id="run")

    def test_metadata_refresh_cannot_refill_explicit_budget_snapshot(self):
        p = profile(remaining_requests=1, remaining_checked_at=999)
        p["cost"] = {"per_request": "0.2", "budget_remaining": "0.2", "budget_checked_at": 999}
        broker = self.broker([p])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        self.clock.sleep(10)
        p["evidence"]["checked_at"] = 1009
        p["status_checked_at"] = 1009
        p["subscription"] = {"plan": "a new plan label"}
        p["warnings"] = ["updated metadata"]
        refreshed = self.broker([p])
        state = refreshed.claim(self.jobs(2), run_id="run")
        self.assertEqual(state["completed"], 1)
        self.assertEqual(state["leases"], [])
        row = refreshed.db.execute("SELECT remaining,budget FROM quota_groups").fetchone()
        self.assertEqual(row[0], 0)
        self.assertEqual(Decimal(row[1]), Decimal(0))

    def test_provider_status_expiry_is_enforced(self):
        p = profile()
        p["status_expires_at"] = 1001
        broker = self.broker([p])
        self.clock.sleep(1)
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])

    def test_validate_record_rejects_wrong_job_token_and_changed_dependency(self):
        broker = self.broker()
        jobs = self.jobs(2)
        jobs[1]["depends_on"] = ["0"]
        lease = broker.claim(jobs, run_id="run")["leases"][0]
        with self.assertRaisesRegex(ValueError, "Unknown"):
            broker.validate_record(run_id="run", job_id="1", token=lease["token"], jobs=jobs)
        self.finish(broker, [lease])
        child = broker.claim(jobs, run_id="run")["leases"][0]
        jobs[0]["prompt"] = "changed anchor"
        with self.assertRaisesRegex(ValueError, "Storyboard changed"):
            broker.validate_record(run_id="run", job_id="1", token=child["token"], jobs=jobs)

    def test_missing_completed_output_does_not_unlock_child_or_regenerate(self):
        broker = self.broker()
        jobs = self.jobs(2)
        jobs[1]["depends_on"] = ["0"]
        lease = broker.claim(jobs, run_id="run")["leases"][0]
        broker.record(run_id="run", job_id="0", token=lease["token"], outcome={"status": "success"})
        state = broker.claim(jobs, run_id="run")
        self.assertEqual(state["leases"], [])
        self.assertEqual(state["completed"], 0)
        self.assertEqual(state["results"][0]["reason"], "completed_output_missing")

    def test_productive_generation_is_not_limited_by_idle_wait_budget(self):
        broker = self.broker([profile(slots=1)], max_wait_seconds=1)
        def generate(job, route, attempt):
            self.clock.sleep(100)
            Path(job["image"]).write_bytes(b"test image")
            return {"status": "success"}
        state = broker.run(self.jobs(3), generate, run_id="run")
        self.assertEqual(state["completed"], 3)

    def test_ambiguous_attempt_holds_capacity_until_resolved(self):
        broker = self.broker([profile(slots=1)])
        leases = broker.claim(self.jobs(1), run_id="run")["leases"]
        self.finish(broker, leases, "ambiguous")
        self.assertEqual(broker.claim(self.jobs(2), run_id="run")["leases"], [])
        self.finish(broker, leases)
        self.assertEqual(len(broker.claim(self.jobs(2), run_id="run")["leases"]), 1)

    def test_exhausted_ineligible_alias_blocks_shared_group(self):
        full = profile("a", "same", quota_windows=[{"used_percent": 100, "resets_at": 9999, "window_minutes": 60}])
        full["eligible"] = False
        full["blocked_reasons"] = ["provider quota window exhausted; refresh status"]
        broker = self.broker([full, profile("b", "same")])
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])

    def test_simultaneous_processes_share_atomic_reservations(self):
        p = profile(slots=4, remaining_requests=3)
        self.broker([p])  # Initialize schema before simultaneous processes connect.
        jobs = self.jobs(6)
        context = multiprocessing.get_context("spawn")
        processes, pipes = [], []
        try:
            for _ in range(2):
                parent, child = context.Pipe()
                process = context.Process(target=_process_claim, args=(str(self.path / "state.sqlite"), p, jobs, child))
                process.start()
                child.close()
                processes.append(process)
                pipes.append(parent)
            for pipe in pipes:
                self.assertTrue(pipe.poll(15), "Broker subprocess failed to initialize")
                self.assertEqual(pipe.recv(), "ready")
            for pipe in pipes:
                pipe.send("claim")
            leases = []
            for pipe in pipes:
                self.assertTrue(pipe.poll(15), "Broker subprocess failed to claim")
                leases.extend(pipe.recv())
        finally:
            for pipe in pipes:
                pipe.close()
            for process in processes:
                process.join(2)
                if process.is_alive():
                    process.terminate()
                    process.join(2)
        self.assertEqual(len(leases), 3)
        self.assertEqual(len({lease["job_id"] for lease in leases}), 3)

    def test_reference_job_keeps_scarce_route_available(self):
        a, b = profile("a", slots=1), profile("b", slots=1)
        b["supports_references"] = False
        broker = self.broker([a, b])
        jobs = self.jobs(2)
        jobs[1]["requires_references"] = True
        leases = broker.claim(jobs, run_id="run")["leases"]
        self.assertEqual({lease["job_id"]: lease["route_id"] for lease in leases}, {"0": "b", "1": "a"})

    def test_stale_boolean_review_cannot_approve_new_art(self):
        jobs = self.jobs(2)
        jobs[0].update(review_required=True, reviewed=True)
        jobs[1]["depends_on"] = ["0"]
        broker = self.broker()
        self.finish(broker, broker.claim(jobs, run_id="run")["leases"])
        result = broker.claim(jobs, run_id="run")
        self.assertEqual(result["leases"], [])
        self.assertEqual(result["results"][0]["status"], "review_required")
        self.assertEqual(result["results"][0]["reason"], "awaiting_review_token")

    @unittest.skipUnless(os.name == "posix", "POSIX permission check")
    def test_new_journal_is_private(self):
        self.broker()
        self.assertEqual((self.path / "state.sqlite").stat().st_mode & 0o777, 0o600)

    def test_expired_status_alias_cannot_restore_exhausted_shared_quota(self):
        full = profile("a", "same", quota_windows=[{"used_percent": 100, "resets_at": 1001, "window_minutes": 60}])
        full["status_expires_at"] = 1001
        self.broker([full, profile("b", "same")])
        self.clock.sleep(10)
        stale = copy.deepcopy(full)
        stale["limits"]["quota_windows"][0]["used_percent"] = 0
        broker = self.broker([stale, profile("b", "same")])
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])

    def test_replaced_output_cannot_unlock_dependent_jobs(self):
        broker = self.broker()
        jobs = self.jobs(2)
        jobs[1]["depends_on"] = ["0"]
        self.finish(broker, broker.claim(jobs, run_id="run")["leases"])
        Path(jobs[0]["image"]).write_bytes(b"replaced externally")
        result = broker.claim(jobs, run_id="run")
        self.assertEqual(result["leases"], [])
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["results"][0]["reason"], "completed_output_changed")

    def test_untrusted_newer_alias_cannot_replenish_group(self):
        good = profile("good", "account", remaining_requests=1)
        good["cost"] = {"per_request": 1, "budget_remaining": 1}
        broker = self.broker([good])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        self.clock.sleep(10)
        for missing_trust in ("authorized", "entitlement", "source"):
            fake = profile("fake", "account", remaining_requests=99,
                           quota_windows=[{"used_percent": 100, "resets_at": 9999, "window_minutes": 60}])
            fake["eligible"] = False
            fake["blocked_reasons"] = ["provider quota window exhausted; refresh status"]
            fake["cost"] = {"per_request": 1, "budget_remaining": 99}
            fake["evidence"]["checked_at"] = 1009
            if missing_trust == "authorized":
                fake["authorized"] = False
            elif missing_trust == "entitlement":
                fake["entitlement"] = "unverified"
            else:
                fake["evidence"]["source"] = "unknown"
            with self.subTest(missing_trust=missing_trust):
                other = self.broker([good, fake])
                self.assertEqual(other.claim(self.jobs(2), run_id="run")["leases"], [])
                row = other.db.execute("SELECT remaining,budget,blocked_reason FROM quota_groups").fetchone()
                self.assertEqual(tuple(row), (0, "0", None))

    def test_trusted_exhausted_alias_blocks_but_cannot_replenish(self):
        good = profile("good", "account", remaining_requests=1)
        good["cost"] = {"per_request": 1, "budget_remaining": 1}
        broker = self.broker([good])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        self.clock.sleep(10)
        full = profile("full", "account", remaining_requests=99,
                       quota_windows=[{"used_percent": 100, "resets_at": 9999, "window_minutes": 60}])
        full.update(eligible=False, blocked_reasons=["provider quota window exhausted; refresh status"])
        full["cost"] = {"per_request": 1, "budget_remaining": 99}
        full["evidence"]["checked_at"] = 1009
        other = self.broker([good, full])
        row = other.db.execute("SELECT remaining,budget,blocked_reason FROM quota_groups").fetchone()
        self.assertEqual(tuple(row), (0, "0", "quota_window_exhausted"))

    def test_fresh_snapshot_subtracts_old_outstanding_reservations(self):
        for status in ("in_flight", "ambiguous"):
            with self.subTest(status=status):
                p = profile(status, status, slots=3, remaining_requests=1)
                p["cost"] = {"per_request": 1, "budget_remaining": 1}
                broker = self.broker([p])
                jobs = [{"id": status + str(i), "prompt": "scene"} for i in range(2)]
                leases = broker.claim(jobs, run_id="run")["leases"]
                if status == "ambiguous":
                    self.finish(broker, leases, "ambiguous")
                self.clock.sleep(10)
                p["evidence"]["checked_at"] = self.clock()-1
                refreshed = self.broker([p])
                self.assertEqual(refreshed.claim(jobs, run_id="run")["leases"], [])
                row = refreshed.db.execute("SELECT remaining,budget FROM quota_groups WHERE group_id=?", (status,)).fetchone()
                self.assertEqual(tuple(row), (0, "0"))

    def test_finalized_old_attempt_can_use_new_snapshot_without_double_count(self):
        p = profile(remaining_requests=1)
        p["cost"] = {"per_request": 1, "budget_remaining": 1}
        broker = self.broker([p])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        self.clock.sleep(10)
        p["evidence"]["checked_at"] = 1009
        refreshed = self.broker([p])
        self.assertEqual(len(refreshed.claim(self.jobs(2), run_id="run")["leases"]), 1)

    def test_rejects_nonfinite_or_noninteger_execution_limits(self):
        for field, values in (
            ("max_wait_seconds", [float("nan"), float("inf"), -float("inf"), True, "60", -1, 10**400]),
            ("max_in_flight", [0, -1, True, 1.0, "1", float("inf")]),
            ("max_attempts", [0, -1, True, 1.0, "1", float("nan")]),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.broker(**{field: value})

    def test_retry_after_numeric_overflow_uses_bounded_fallback(self):
        broker = self.broker()
        leases = broker.claim(self.jobs(1), run_id="run")["leases"]
        self.finish(broker, leases, "rate_limited", retry_after=10**400)
        self.assertEqual(broker.db.execute("SELECT cooldown_until FROM quota_groups").fetchone()[0], 1060)

    def test_multiple_exhausted_windows_still_block_account_aliases(self):
        full = profile("a", "shared", quota_windows=[
            {"used_percent": 100, "resets_at": 2000, "window_minutes": 60},
            {"used_percent": 100, "resets_at": 9000, "window_minutes": 10080},
        ])
        full.update(eligible=False, blocked_reasons=[
            "provider quota window exhausted; refresh status",
            "provider quota window exhausted; refresh status",
        ])
        broker = self.broker([full, profile("b", "shared")])
        self.assertEqual(broker.claim(self.jobs(1), run_id="run")["leases"], [])

    def test_currency_change_on_reopen_is_rejected_without_mutating_budget(self):
        p = profile()
        p["cost"] = {"per_request": 1, "budget_remaining": 2, "currency": "USD"}
        broker = self.broker([p])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        p["cost"]["currency"] = "EUR"
        with self.assertRaisesRegex(ValueError, "Currency changed"):
            self.broker([p])
        row = broker.db.execute("SELECT currency,budget FROM quota_groups").fetchone()
        self.assertEqual(tuple(row), ("USD", "1"))
        p["cost"]["currency"] = "USD"
        same_currency = self.broker([p])
        self.assertEqual(len(same_currency.claim(self.jobs(2), run_id="run")["leases"]), 1)

    def test_legacy_ledger_without_currency_requires_reconciliation(self):
        broker = self.broker()
        broker.db.execute("ALTER TABLE quota_groups DROP COLUMN currency")
        with self.assertRaisesRegex(ValueError, "Legacy quota ledger.*currency"):
            self.broker()

    def test_future_provider_status_blocks_without_missing_group_error(self):
        p = profile()
        p["status_checked_at"] = 1001
        broker = self.broker([p])
        result = broker.claim(self.jobs(1), run_id="run")
        self.assertEqual(result["leases"], [])
        self.assertEqual(result["blockers"][0]["routes"][0]["reason"], "provider_status_from_future")

    def test_equal_timestamp_snapshot_can_only_lower_balance(self):
        p = profile(remaining_requests=3)
        p["cost"] = {"per_request": 1, "budget_remaining": 3}
        broker = self.broker([p])
        self.finish(broker, broker.claim(self.jobs(1), run_id="run")["leases"])
        p["limits"]["remaining_requests"] = 0
        p["cost"]["budget_remaining"] = 0
        lower = self.broker([p])
        self.assertEqual(lower.claim(self.jobs(2), run_id="run")["leases"], [])
        row = lower.db.execute("SELECT remaining,budget FROM quota_groups").fetchone()
        self.assertEqual(tuple(row), (0, "0"))
        p["limits"]["remaining_requests"] = 99
        p["cost"]["budget_remaining"] = 99
        higher = self.broker([p])
        self.assertEqual(higher.claim(self.jobs(2), run_id="run")["leases"], [])


if __name__ == "__main__":
    unittest.main()
