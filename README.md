# unison-io-core

[![Docker CI](https://github.com/project-unisonos/unison-io-core/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/project-unisonos/unison-io-core/actions/workflows/docker-ci.yml)

On-device multimodal runtime stub for Developer Mode. Emits EventEnvelopes to the Orchestrator and does not persist identity or secrets.

## Run locally

- Python
  - pip install -r requirements.txt
  - python src/server.py
  - Open: [http://localhost:8085/health](http://localhost:8085/health)

- Docker
  - docker build -t unison-io-core:dev .
  - docker run --rm -p 8085:8085 -e UNISON_ORCH_HOST=host.docker.internal -e UNISON_ORCH_PORT=8080 unison-io-core:dev

## Test forwarding

PowerShell:

```powershell
$body = @'
{
  "timestamp": "2025-10-28T00:00:00Z",
  "source": "io-core",
  "intent": "echo",
  "payload": { "message": "hello" }
}
'@
Invoke-RestMethod -Uri http://localhost:8085/io/emit -Method POST -ContentType 'application/json' -Body $body
```

## Environment

- UNISON_ORCH_HOST (default orchestrator)
- UNISON_ORCH_PORT (default 8080)

## Notes

- Intended for Developer Mode; no persistence; models are pluggable later.
