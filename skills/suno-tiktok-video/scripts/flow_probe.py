#!/usr/bin/env python3
"""
flow_probe.py - Zero-friction probe for Google Flow Automation availability.
Detects if local server (:18999) is running, if the Chrome extension is connected,
and what rendering strategy should be selected (hybrid_i2v vs static_fallback).
"""
import json
import urllib.request
import urllib.error
import time
from typing import Dict, Any, Optional

DEFAULT_ENDPOINT = "http://127.0.0.1:18999/api/health"

def probe_flow_environment(endpoint: str = DEFAULT_ENDPOINT, timeout: float = 0.8) -> Dict[str, Any]:
    """
    Probes the Google Flow automation gateway.
    Execution completes in < 800ms.
    Returns:
      {
        "available": bool,
        "mode": "hybrid_i2v" | "static_fallback",
        "reason": str,
        "model": Optional[str],
        "extension_connected": bool,
        "flow_tab_active": bool,
        "flow_state": str
      }
    """
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "flow-probe/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return {
                    "available": False,
                    "mode": "static_fallback",
                    "reason": f"Server responded with status {resp.status}",
                    "model": None,
                    "extension_connected": False,
                    "flow_tab_active": False,
                    "flow_state": "server_error"
                }
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionRefusedError, OSError) as e:
        err_msg = str(getattr(e, 'reason', e))
        return {
            "available": False,
            "mode": "static_fallback",
            "reason": f"Flow local server unreachable: {err_msg}",
            "model": None,
            "extension_connected": False,
            "flow_tab_active": False,
            "flow_state": "offline"
        }
    except Exception as e:
        return {
            "available": False,
            "mode": "static_fallback",
            "reason": f"Probe error: {str(e)}",
            "model": None,
            "extension_connected": False,
            "flow_tab_active": False,
            "flow_state": "unknown_error"
        }

    ext = data.get("extension", {})
    is_connected = bool(ext.get("connected"))
    flow_state = ext.get("flowState", "unknown")
    flow_tab_active = bool(ext.get("flowTabActive"))

    # If extension is alive and tab is present/ready or in project, user intent for video is active
    if is_connected:
        if flow_state in ("dashboard", "in_project") or flow_tab_active:
            return {
                "available": True,
                "mode": "hybrid_i2v",
                "reason": f"Google Flow active (state: {flow_state})",
                "model": data.get("model", "Veo 3.1 - Lite"),
                "extension_connected": True,
                "flow_tab_active": flow_tab_active,
                "flow_state": flow_state
            }
        elif flow_state == "no_tab":
            # Extension is alive, but tab needs to be opened
            return {
                "available": True,
                "mode": "hybrid_i2v",
                "reason": "Extension connected; flow tab will be auto-opened",
                "model": data.get("model", "Veo 3.1 - Lite"),
                "extension_connected": True,
                "flow_tab_active": False,
                "flow_state": "no_tab"
            }
        else:
            return {
                "available": False,
                "mode": "static_fallback",
                "reason": f"Google Flow session state not ready: {flow_state}",
                "model": None,
                "extension_connected": True,
                "flow_tab_active": False,
                "flow_state": flow_state
            }

    return {
        "available": False,
        "mode": "static_fallback",
        "reason": "Chrome extension not polling or sleeping",
        "model": None,
        "extension_connected": False,
        "flow_tab_active": False,
        "flow_state": "sleeping"
    }

if __name__ == "__main__":
    result = probe_flow_environment()
    print(json.dumps(result, indent=2, ensure_ascii=False))
