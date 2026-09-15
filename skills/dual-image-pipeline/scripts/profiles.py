"""Validate non-secret route evidence without treating a plan name as capacity."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re
import shutil
import time


SOURCES = {"host_tool", "provider_status", "user_confirmed", "authorized_smoke_test"}


def discover() -> dict:
    """Executable discovery is deliberately not an entitlement or image probe."""
    return {"candidates": [
        {"id": name, "executable": path, "image_capability": "unverified",
         "subscription": "unknown", "eligible": False}
        for name in ("codex", "agy", "gemini")
        if (path := shutil.which(name))
    ], "host_tools": "Inspect the tools exposed by the active host separately"}


def number(value, field: str, *, integer=False, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum or (integer and int(value) != value):
        raise ValueError(f"Invalid {field}")
    return int(value) if integer else value


def normalize_profiles(data: dict, now: float | None = None) -> list[dict]:
    now = time.time() if now is None else now
    number(now, "current time")
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data.get("schema_version") != 1:
        raise ValueError("Route profiles require schema_version: 1")
    if not isinstance(data.get("routes"), list) or not data["routes"]:
        raise ValueError("Profiles must contain a nonempty routes list")
    routes, seen = [], set()
    for raw in data["routes"]:
        if not isinstance(raw, dict):
            raise ValueError("Each route must be an object")
        route = copy.deepcopy(raw)
        route_id = route.get("id")
        if not isinstance(route_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", route_id) or route_id in seen:
            raise ValueError("Route IDs must be unique labels using letters, digits, underscore, dot or dash")
        seen.add(route_id)
        reasons, warnings = [], []
        if not isinstance(route.get("kind"), str) or route["kind"] not in {"host_tool", "cli", "local"}:
            raise ValueError(f"{route_id}: unsupported route kind")
        group = route.get("quota_group")
        if not isinstance(group, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", group):
            raise ValueError(f"{route_id}: quota_group is required (same account = same group)")
        for field in ("image_capability", "authorized"):
            if route.get(field) is not True:
                reasons.append(f"{field} is not confirmed")
        if route.get("entitlement") != "verified":
            reasons.append("entitlement is unverified or denied")
        sub = route.get("subscription", {})
        if not isinstance(sub, dict):
            raise ValueError(f"{route_id}: subscription must be an object")
        if not isinstance(sub.get("kind"), str) or sub["kind"] not in {"subscription", "api", "local"}:
            reasons.append("billing/access type is unknown")
        if not sub.get("plan"):
            warnings.append("plan name unknown; no capacity inferred from the name")
        evidence = route.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError(f"{route_id}: evidence must be an object")
        if not isinstance(evidence.get("source"), str) or evidence["source"] not in SOURCES:
            reasons.append("missing evidence source")
        checked = number(evidence.get("checked_at", 0), "checked_at")
        expires = number(evidence.get("expires_at", 0), "expires_at")
        if not checked or checked > now + 5 or expires <= now or expires <= checked:
            reasons.append("evidence missing, expired, or from the future")
        if route.get("status_checked_at") is not None or route.get("status_expires_at") is not None:
            status_checked = number(route.get("status_checked_at", 0), "status_checked_at")
            status_expires = number(route.get("status_expires_at", 0), "status_expires_at")
            if not status_checked or status_checked > now + 5 or status_expires <= now or status_expires <= status_checked:
                reasons.append("provider status missing, expired, or from the future")
        limits = route.setdefault("limits", {})
        if not isinstance(limits, dict):
            raise ValueError(f"{route_id}: limits must be an object")
        if limits.get("max_parallel") is None:
            limits["max_parallel"] = 1
            warnings.append("parallel limit unknown; conservative cap 1")
        limit = number(limits["max_parallel"], "max_parallel", integer=True, minimum=1)
        initial = number(limits.setdefault("initial_parallel", 1), "initial_parallel", integer=True, minimum=1)
        if initial > limit:
            raise ValueError(f"{route_id}: initial_parallel exceeds max_parallel")
        for key in ("requests_per_minute", "requests_per_day", "remaining_requests"):
            if limits.get(key) is not None:
                limits[key] = number(limits[key], key, integer=True)
        if limits.get("remaining_requests") is not None:
            observed = number(limits.setdefault("remaining_checked_at", checked), "remaining_checked_at")
            if observed > now + 5:
                reasons.append("remaining request snapshot is from the future")
        if limits.get("reset_at") is not None:
            number(limits["reset_at"], "reset_at")
        windows = limits.get("quota_windows", [])
        if not isinstance(windows, list):
            raise ValueError("quota_windows must be a list")
        for window in windows:
            if not isinstance(window, dict):
                raise ValueError("Each quota window must be an object")
            used = number(window.get("used_percent"), "used_percent")
            if used > 100:
                raise ValueError("used_percent exceeds 100")
            number(window.get("resets_at"), "resets_at")
            number(window.get("window_minutes"), "window_minutes", minimum=1)
            if used >= 100:
                reasons.append("provider quota window exhausted; refresh status")
        if limits.get("remaining_requests") is None:
            warnings.append("remaining image count unknown; quota percentages are not image counts")
        cost = route.get("cost", {})
        if not isinstance(cost, dict):
            raise ValueError("cost must be an object")
        if cost.get("per_request") is None:
            reasons.append("per-request cost upper bound is unknown")
        else:
            number(cost["per_request"], "per_request")
            if cost["per_request"] > 0 and cost.get("budget_remaining") is None:
                reasons.append("paid route has no approved remaining budget")
        if cost.get("budget_remaining") is not None:
            number(cost["budget_remaining"], "budget_remaining")
            observed = number(cost.setdefault("budget_checked_at", checked), "budget_checked_at")
            if observed > now + 5:
                reasons.append("budget snapshot is from the future")
        if sub.get("kind") == "api" and cost.get("per_request") == 0 and route.get("zero_cost_verified") is not True:
            reasons.append("API zero price has not been verified")
        if sub.get("kind") == "subscription" and cost.get("per_request") == 0 and route.get("overage_disabled") is not True:
            reasons.append("included-only route requires verified disabled paid overages")
        if route.get("kind") in {"cli", "local"}:
            command = route.get("command")
            if (not isinstance(command, list) or not command or
                    not all(isinstance(s, str) and s for s in command)):
                reasons.append("missing verified adapter command (JSON stdin/stdout)")
            elif not shutil.which(command[0]):
                reasons.append("adapter executable not found")
        if route.get("supports_references") is not None and type(route["supports_references"]) is not bool:
            raise ValueError("supports_references must be boolean")
        route["supports_references"] = route.get("supports_references") is True
        route["timeout_seconds"] = number(route.get("timeout_seconds", 600), "timeout_seconds", minimum=1)
        route["eligible"] = not reasons
        route["blocked_reasons"] = reasons
        route["warnings"] = warnings
        routes.append(route)
    # Distinct routes on one account must not invent distinct billing units.
    currencies = {}
    for route in routes:
        group = route["quota_group"]
        currency = route.get("cost", {}).get("currency", "USD")
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Budget currency must be a three-letter uppercase code")
        if group in currencies and currency != currencies[group]:
            raise ValueError(f"Conflicting budget currencies in quota group {group}")
        currencies[group] = currency
    return routes


def load_profiles(path: Path) -> list[dict]:
    return normalize_profiles(json.loads(path.read_text(encoding="utf-8")))


def plan(routes: list[dict], max_in_flight: int) -> dict:
    max_in_flight = number(max_in_flight, "max_in_flight", integer=True, minimum=1)
    groups = {}
    for route in routes:
        if route["eligible"]:
            cap = route["limits"]["max_parallel"]
            group = route["quota_group"]
            groups[group] = min(groups.get(group, cap), cap)
    summaries = []
    for route in routes:
        # Raw adapter arguments, account fields and extension keys may contain
        # secrets. Only validated, explicitly public fields enter printed plans.
        summary = {key: route.get(key) for key in
                   ("id", "kind", "quota_group", "eligible", "blocked_reasons", "warnings",
                    "status_checked_at", "status_expires_at")}
        summary["limits"] = {key: route["limits"][key] for key in
                             ("max_parallel", "initial_parallel", "requests_per_minute",
                              "requests_per_day", "remaining_requests", "remaining_checked_at", "reset_at")
                             if key in route["limits"]}
        if "quota_windows" in route["limits"]:
            summary["limits"]["quota_windows"] = [
                {key: window[key] for key in ("used_percent", "resets_at", "window_minutes")}
                for window in route["limits"]["quota_windows"]]
        subscription = route.get("subscription", {})
        label = subscription.get("plan")
        if (not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_. -]{1,80}", label)
                or label.lower().startswith(("sk-", "sk_", "ya29.", "bearer "))):
            label = None
        summary["subscription"] = {"kind": subscription.get("kind")
                                   if isinstance(subscription.get("kind"), str) and subscription.get("kind") in {"subscription", "api", "local"} else None,
                                   "plan": label}
        summary["cost"] = {key: route.get("cost", {})[key] for key in
                           ("per_request", "budget_remaining", "budget_checked_at", "currency") if key in route.get("cost", {})}
        evidence = route.get("evidence", {})
        summary["evidence"] = {"source": evidence.get("source") if isinstance(evidence.get("source"), str) and evidence.get("source") in SOURCES else None,
                               "checked_at": evidence.get("checked_at"), "expires_at": evidence.get("expires_at")}
        summaries.append(summary)
    return {"eligible_capacity_ceiling": min(max_in_flight, sum(groups.values())),
            "note": "A ceiling, not a throughput promise; current quota, dependencies and cooldowns apply",
            "routes": summaries}
