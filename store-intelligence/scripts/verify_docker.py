"""Verify docker compose API — health, metrics, ingest idempotency."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
REFERENCE_DATE = "2026-04-10"
DOCKER_BIN = r"C:\Program Files\Docker\Docker\resources\bin"


def _curl(path: str) -> tuple[int, dict | str]:
    try:
        with urlopen(f"{BASE}{path}", timeout=10) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except (URLError, OSError) as exc:
        return 0, str(exc)


def _post_ingest(events: list[dict]) -> tuple[int, dict]:
    import urllib.request

    payload = json.dumps({"events": events}).encode()
    req = urllib.request.Request(
        f"{BASE}/events/ingest",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except (URLError, OSError) as exc:
        return 0, {"error": str(exc)}


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = None
    if sys.platform == "win32" and (Path(DOCKER_BIN) / "docker.exe").exists():
        env = {**os.environ, "PATH": DOCKER_BIN + ";" + os.environ.get("PATH", "")}
    return subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, env=env)


def main() -> int:
    print("=" * 60)
    print("DOCKER VERIFICATION")
    print("=" * 60)

    up = _run(["docker", "compose", "up", "-d", "--build"])
    if up.returncode != 0:
        print("FAIL: docker compose up")
        print(up.stderr or up.stdout)
        return 1
    print("OK: docker compose up -d --build")
    time.sleep(5)

    for attempt in range(30):
        code, body = _curl("/health")
        if code == 200 and isinstance(body, dict) and body.get("status") == "OK":
            print(f"OK: /health ({attempt + 1} tries)")
            break
        time.sleep(2)
    else:
        print("FAIL: /health not ready after 60s")
        logs = _run(["docker", "compose", "logs", "--tail", "40"])
        print(logs.stdout or logs.stderr)
        return 1

    code_dash, dash = _curl("/dashboard")
    if code_dash != 200 or not isinstance(dash, str) or "Live replay" not in dash:
        print(f"FAIL: /dashboard {code_dash}")
        return 1
    print("OK: /dashboard (Part E UI)")

    code, metrics = _curl(f"/stores/ST1008/metrics?date={REFERENCE_DATE}")
    if code != 200 or not isinstance(metrics, dict):
        print(f"FAIL: metrics {code} {metrics}")
        return 1
    print(f"OK: metrics unique_visitors={metrics.get('unique_visitors')}")

    sample_path = ROOT / "data" / "sample_events.jsonl"
    events = [json.loads(l) for l in sample_path.read_text().splitlines() if l.strip()][:5]
    code, ingest = _post_ingest(events)
    if code != 200:
        print(f"FAIL: ingest {code} {ingest}")
        return 1
    code2, ingest2 = _post_ingest(events)
    if ingest.get("accepted") != ingest2.get("accepted"):
        print(f"FAIL: idempotency {ingest} vs {ingest2}")
        return 1
    print(f"OK: ingest idempotent ({ingest['accepted']} accepted)")

    ps = _run(["docker", "compose", "ps"])
    print("\nContainer status:")
    print(ps.stdout or ps.stderr)
    print("\nAll Docker checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
