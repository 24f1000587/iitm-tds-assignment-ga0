from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import time
import uuid
import logging
import json
from collections import deque

app = FastAPI()

# Startup time
START_TIME = time.time()

# Prometheus Counter
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP Requests"
)

# Store last logs
LOGS = deque(maxlen=1000)

# Logger
logger = logging.getLogger("observability")
logger.setLevel(logging.INFO)


@app.middleware("http")
async def metrics_and_logging(request: Request, call_next):
    REQUEST_COUNTER.inc()

    request_id = str(uuid.uuid4())

    response = await call_next(request)

    entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    LOGS.append(entry)
    logger.info(json.dumps(entry))

    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/work")
def work(n: int):
    # simulate work
    total = 0
    for i in range(n):
        total += i

    return {
        "email": "24f1000587@ds.study.iitm.ac.in",
        "done": n
    }


@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME
    }


@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    return list(LOGS)[-limit:]


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )