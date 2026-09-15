"""Read public account/limit fields from Codex App Server; never expose credentials."""
from __future__ import annotations

import json
import math
import queue
import shutil
import subprocess
import threading
import time


ACCOUNT_TYPES = {"chatgpt", "apiKey", "amazonBedrock"}
# Public labels from the App Server schema. These labels never imply capacity.
PLAN_TYPES = {
    "free", "go", "plus", "pro", "prolite", "team", "self_serve_business_prolite",
    "self_serve_business_usage_based", "business", "ent26", "enterprise_cbp_automation",
    "enterprise_cbp_usage_based", "enterprise", "edu", "edu_plus", "edu_pro", "unknown",
}


def _label(value, allowed):
    return value if isinstance(value, str) and value in allowed else None


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def sanitize(account_result: dict, limit_result: dict, now=None) -> dict:
    """Only allowlisted fields leave the RPC reader (never email, tokens or IDs)."""
    now = time.time() if now is None else now
    account = account_result.get("account") if isinstance(account_result, dict) else None
    account = account if isinstance(account, dict) else {}
    snapshot = limit_result.get("rateLimits") if isinstance(limit_result, dict) else None
    # Model-specific rateLimitsByLimitId cannot safely identify the image route;
    # no applicable general snapshot means quota remains unknown.
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    windows = []
    valid_windows = True
    for key in ("primary", "secondary"):
        raw = snapshot.get(key)
        if raw is None:
            continue
        if not isinstance(raw, dict):
            valid_windows = False
            continue
        values = [raw.get("usedPercent"), raw.get("resetsAt"), raw.get("windowDurationMins")]
        if any(not _finite_number(v) for v in values):
            valid_windows = False
            continue
        used, resets, duration = values
        if 0 <= used <= 100 and resets > 0 and duration > 0:
            windows.append({"used_percent": used, "resets_at": resets, "window_minutes": duration})
        else:
            valid_windows = False
    return {"source": "codex_app_server", "checked_at": now, "expires_at": now + 300,
            "account_type": _label(account.get("type"), ACCOUNT_TYPES), "plan": _label(account.get("planType"), PLAN_TYPES),
            "quota_windows": windows, "quota_available": bool(windows) and valid_windows,
            "remaining_requests": None, "max_parallel": None,
            "scope": "Local Codex CLI account; verify it is the account used by the image route"}


def probe(binary="codex", timeout=15) -> dict:
    if not shutil.which(binary):
        return {"source": "codex_app_server", "available": False, "reason": "codex executable missing"}
    proc = None
    messages = queue.Queue()

    def read():
        for line in proc.stdout:
            try:
                messages.put(json.loads(line))
            except (ValueError, TypeError):
                continue

    deadline = time.monotonic() + timeout

    def send(payload):
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()

    def request(method, params, request_id):
        send({"method": method, "params": params, "id": request_id})
        while time.monotonic() < deadline:
            try:
                message = messages.get(timeout=max(0.001, deadline - time.monotonic()))
            except queue.Empty:
                break
            if isinstance(message, dict) and message.get("id") == request_id:
                # Error content can contain identifiers; never return it verbatim.
                return message.get("result") if "error" not in message else None
        raise TimeoutError("Codex status request timed out")

    try:
        proc = subprocess.Popen([binary, "app-server", "--stdio"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        initialized = request("initialize", {"clientInfo": {
            "name": "image_pipeline_status", "title": "Image pipeline status", "version": "1.0"}}, 1)
        if not isinstance(initialized, dict):
            return {"available": False, "reason": "Codex initialize unsupported"}
        send({"method": "initialized", "params": {}})
        account = request("account/read", {"refreshToken": False}, 2)
        if not isinstance(account, dict):
            return {"available": False, "reason": "Account status unavailable"}
        account_data = account.get("account")
        account_type = account_data.get("type") if isinstance(account_data, dict) else None
        limits = request("account/rateLimits/read", {}, 3) if account_type == "chatgpt" else {}
        result = sanitize(account, limits or {})
        result["available"] = True
        result["quota_status"] = ("available" if result["quota_available"] else
                                  "request_failed" if limits is None else "unknown")
        return result
    except (OSError, TimeoutError, ValueError):
        return {"available": False, "reason": "Status unavailable; no entitlement or quota inferred"}
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        for stream in (proc.stdin, proc.stdout) if proc is not None else ():
            if stream:
                stream.close()


def refresh(routes: list[dict], snapshot: dict) -> None:
    """Update only explicitly bound routes; a status read never authorizes spending."""
    for route in routes:
        if route.get("status_source") != "codex_app_server":
            continue
        subscription = route.get("subscription")
        if not isinstance(subscription, dict) or subscription.get("kind") != "subscription":
            # The CLI account cannot establish billing for an API/local route,
            # even if both use the same vendor or local executable.
            route["entitlement"] = "unknown"
            continue
        if not snapshot.get("available") or snapshot.get("account_type") != "chatgpt" or not snapshot.get("quota_available"):
            route["entitlement"] = "unknown"
            continue
        # A general CLI login does not establish image capability.
        route["subscription"] = {**subscription, "plan": snapshot.get("plan")}
        # Account workload status cannot renew image authorization or replenish
        # numerical image/budget balances whose source uses different units.
        route["status_checked_at"] = snapshot["checked_at"]
        route["status_expires_at"] = snapshot["expires_at"]
        route.setdefault("limits", {})["quota_windows"] = snapshot["quota_windows"]
        # No numerical conversions from workload percentage to image counts.
