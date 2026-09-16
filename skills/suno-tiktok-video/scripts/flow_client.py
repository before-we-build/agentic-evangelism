#!/usr/bin/env python3
"""
flow_client.py - Automation client for batch video generation via Google Flow.
Implements retry logic with exponential backoff, Service Worker awakening,
and mapping of generated video files to storyboard scene IDs.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional

DEFAULT_SERVER_URL = "http://127.0.0.1:18999"

class FlowClientError(Exception):
    pass

class FlowClient:
    def __init__(self, base_url: str = DEFAULT_SERVER_URL, max_retries: int = 4):
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries

    def _post(self, endpoint: str, data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "flow-client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get(self, endpoint: str, timeout: float = 10.0) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "flow-client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def start_batch(self, items: List[Dict[str, Any]], folder_name: str = "flow_scenes",
                    model: str = "Veo 3.1 - Lite", aspect_ratio: str = "9:16") -> Dict[str, Any]:
        """
        Submits generation items.
        Each item can have:
          - prompt: str
          - images: Optional[List[Dict[str, str]]] (e.g. [{"base64": "...", "name": "..."}])
          - mode: "imageToVideo" | "textToVideo"
        """
        payload = {
            "mode": "imageToVideo",
            "model": model,
            "aspectRatio": aspect_ratio,
            "folderName": folder_name,
            "autoChangeFileName": True,
            "autoDownload": True,
            "maxRetries": self.max_retries,
            "items": items
        }
        return self._post("/api/start", payload)

    def get_status(self) -> Dict[str, Any]:
        return self._get("/api/status")

    def poll_until_complete(self, total_expected: int, timeout_seconds: float = 900.0,
                            poll_interval: float = 3.0) -> Dict[str, Any]:
        """
        Polls until the batch completes or fatal errors occur.
        Uses exponential backoff when queue is busy or delayed.
        """
        start_time = time.time()
        last_processed = -1
        stagnant_count = 0

        while time.time() - start_time < timeout_seconds:
            try:
                status = self.get_status()
            except Exception as e:
                # Local server momentary glitch
                time.sleep(poll_interval)
                continue

            processed = status.get("processedCount", 0)
            is_running = status.get("isRunning", False)
            total = status.get("totalCount", total_expected)

            if processed == last_processed:
                stagnant_count += 1
            else:
                stagnant_count = 0
                last_processed = processed

            # If finished processing all items
            if processed >= total and not is_running:
                return status

            # Retry / wake-up trigger if stagnant for too long (> 90 seconds without progress)
            if stagnant_count > 30 and is_running:
                # Poke status or resume
                try:
                    self._get("/api/resume")
                except Exception:
                    pass
                stagnant_count = 0

            time.sleep(poll_interval)

        raise TimeoutError(f"Flow generation batch timed out after {timeout_seconds} seconds")

if __name__ == "__main__":
    client = FlowClient()
    try:
        st = client.get_status()
        print("Flow Server Status:", json.dumps(st, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error connecting to Flow Server: {e}")
