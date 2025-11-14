import os
import uuid
from typing import Any, Dict, Tuple
import logging
import json
import time
from collections import defaultdict

import httpx
from fastapi import FastAPI, Body, Request, HTTPException
import uvicorn
from unison_common import EnvelopeValidationError, validate_event_envelope
from unison_common.logging import configure_logging, log_json

APP_NAME = "unison-io-core"
ORCH_HOST = os.getenv("UNISON_ORCH_HOST", "orchestrator")
ORCH_PORT = os.getenv("UNISON_ORCH_PORT", "8080")

app = FastAPI(title=APP_NAME)
logger = configure_logging("unison-io-core")

# Simple in-memory metrics
_metrics = defaultdict(int)
_start_time = time.time()


def http_post_json(host: str, port: str, path: str, payload: dict, headers: Dict[str, str] | None = None) -> Tuple[bool, int, dict | None]:
    try:
        url = f"http://{host}:{port}{path}"
        merged_headers = {"Accept": "application/json"}
        if headers:
            merged_headers.update(headers)
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, json=payload, headers=merged_headers)
        parsed = None
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
        return (resp.status_code >= 200 and resp.status_code < 300, resp.status_code, parsed)
    except Exception:
        return (False, 0, None)


@app.get("/healthz")
@app.get("/health")
def health(request: Request):
    _metrics["/health"] += 1
    event_id = request.headers.get("X-Event-ID")
    log_json(logging.INFO, "health", service="unison-io-core", event_id=event_id)
    return {"status": "ok", "service": APP_NAME}

@app.get("/metrics")
def metrics():
    """Prometheus text-format metrics."""
    uptime = time.time() - _start_time
    lines = [
        "# HELP unison_io_core_requests_total Total number of requests by endpoint",
        "# TYPE unison_io_core_requests_total counter",
    ]
    for k, v in _metrics.items():
        lines.append(f'unison_io_core_requests_total{{endpoint="{k}"}} {v}')
    lines.extend([
        "",
        "# HELP unison_io_core_uptime_seconds Service uptime in seconds",
        "# TYPE unison_io_core_uptime_seconds gauge",
        f"unison_io_core_uptime_seconds {uptime}",
    ])
    return "\n".join(lines)

@app.get("/readyz")
@app.get("/ready")
def ready(request: Request):
    event_id = request.headers.get("X-Event-ID")
    # Check orchestrator health as downstream dependency
    ok, _, _ = http_post_json(ORCH_HOST, ORCH_PORT, "/health", {}, headers={"X-Event-ID": event_id})
    log_json(logging.INFO, "ready", service="unison-io-core", event_id=event_id, orchestrator_ok=ok, ready=ok)
    return {"ready": ok, "orchestrator": {"host": ORCH_HOST, "port": ORCH_PORT, "ok": ok}}


@app.post("/io/emit")
def io_emit(request: Request, envelope: Dict[str, Any] = Body(...)):
    _metrics["/io/emit"] += 1
    event_id = request.headers.get("X-Event-ID") or str(uuid.uuid4())
    try:
        envelope = validate_event_envelope(envelope)
    except EnvelopeValidationError as exc:
        log_json(
            logging.WARNING,
            "io_emit_invalid_envelope",
            service="unison-io-core",
            event_id=event_id,
            error=str(exc),
        )
        raise HTTPException(status_code=400, detail=f"Invalid event envelope: {exc}") from exc

    log_json(logging.INFO, "io_emit", service="unison-io-core", event_id=event_id, intent=envelope.get("intent"))
    ok, status, body = http_post_json(ORCH_HOST, ORCH_PORT, "/event", envelope, headers={"X-Event-ID": event_id})
    log_json(logging.INFO, "io_emit_result", service="unison-io-core", event_id=event_id, ok=ok, status=status)
    return {
        "ok": ok,
        "status": status,
        "orchestrator": {"host": ORCH_HOST, "port": ORCH_PORT},
        "event_id": event_id,
        "response": body,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
