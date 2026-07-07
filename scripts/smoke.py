from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.environ.get("SMOKE_API_KEY", "dev-key")

_CHECK_REQUEST = {
    "question_id": "smoke",
    "requirements": [
        {"id": "r1", "text": "Personal data is retained no longer than 24 months.",
         "check": {"metric": "retention", "unit": "months", "operator": "at_most", "threshold": 24}},
    ],
    "sources": [{"id": "s1", "kind": "plain_text", "uri": "samples/data_retention_policy.md"}],
    "principal": {"id": "o", "roles": ["owner"]},
}


def _get(path: str):
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=15) as response:
        return response.status, json.loads(response.read().decode())


def _post(path: str, payload: dict):
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode())


def main() -> int:
    status, body = _get("/health")
    if status != 200 or body.get("status") != "ok":
        print(f"FAIL /health: {status} {body}")
        return 1
    print("ok  /health")

    status, body = _post("/compliance/check", _CHECK_REQUEST)
    findings = body.get("findings", [])
    if status != 200 or not findings:
        print(f"FAIL /compliance/check: {status} {body}")
        return 1
    tools = [entry["tool"] for entry in findings[0].get("tool_trace", [])]
    print(f"ok  /compliance/check -> {findings[0]['verdict']} (tools: {tools})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
