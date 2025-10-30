FROM python:3.12-slim

WORKDIR /app

# Python deps
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY src ./src

ENV UNISON_ORCH_HOST=orchestrator \
    UNISON_ORCH_PORT=8080

EXPOSE 8085
CMD ["python", "src/server.py"]
