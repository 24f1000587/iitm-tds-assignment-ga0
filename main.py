import os
import time
import uuid
import json
import logging
from collections import deque
from typing import List

import yaml
import jwt
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Query,
    Header,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

load_dotenv()

EMAIL = "24f1000587@ds.study.iitm.ac.in"

API_KEY = "ak_tv28mpb9ju21g5ttd7umz8ce"

ALLOWED_ORIGIN = "https://dash-71emzk.example.com"

ISSUER = "https://idp.exam.local"

AUDIENCE = "tds-xxkuc9h0.apps.exam.local"

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP Requests",
)

LOGS = deque(maxlen=1000)

logger = logging.getLogger("observability")
logger.setLevel(logging.INFO)

@app.get("/debug")
def debug():
    return {
        "version": "MERGED-340-LINES",
        "routes": [r.path for r in app.routes],
    }

@app.middleware("http")
async def middleware(request: Request, call_next):

    REQUEST_COUNTER.inc()

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    start = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.6f}"

    entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    LOGS.append(entry)

    logger.info(json.dumps(entry))

    return response


#############################################
# CONFIG
#############################################

config = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

yaml_file = "config.development.yaml"

if os.path.exists(yaml_file):
    with open(yaml_file) as f:
        config.update(yaml.safe_load(f) or {})

if os.getenv("APP_PORT"):
    config["port"] = os.getenv("APP_PORT")

if os.getenv("NUM_WORKERS"):
    config["workers"] = os.getenv("NUM_WORKERS")

if os.getenv("APP_LOG_LEVEL"):
    config["log_level"] = os.getenv("APP_LOG_LEVEL")

if os.getenv("APP_DEBUG"):
    config["debug"] = os.getenv("APP_DEBUG")

if os.getenv("APP_API_KEY"):
    config["api_key"] = os.getenv("APP_API_KEY")


def to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def coerce(cfg):
    cfg["port"] = int(cfg["port"])
    cfg["workers"] = int(cfg["workers"])
    cfg["debug"] = to_bool(cfg["debug"])
    cfg["api_key"] = "****"
    return cfg


#############################################
# MODELS
#############################################

class TokenRequest(BaseModel):
    token: str


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: List[Event]


#############################################
# ROOT
#############################################

@app.get("/")
def root():
    return {"status": "running"}


#############################################
# Q1
#############################################

@app.get("/stats")
def stats(values: str):

    nums = [int(x) for x in values.split(",")]

    total = sum(nums)

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": total,
        "min": min(nums),
        "max": max(nums),
        "mean": total / len(nums),
    }


#############################################
# Q2
#############################################

@app.post("/verify")
def verify(req: TokenRequest):

    try:

        payload = jwt.decode(
            req.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }

    except jwt.PyJWTError:

        return JSONResponse(
            status_code=401,
            content={"valid": False},
        )


#############################################
# Q3
#############################################

@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):

    result = config.copy()

    for item in set:

        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        result[key] = value

    return coerce(result)


#############################################
# Q5
#############################################

@app.post("/analytics")
def analytics(
    body: AnalyticsRequest,
    x_api_key: str = Header(None),
):

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )

    revenue = sum(
        e.amount
        for e in body.events
        if e.amount > 0
    )

    totals = {}

    for e in body.events:

        if e.amount > 0:
            totals[e.user] = totals.get(
                e.user,
                0,
            ) + e.amount

    return {
        "email": EMAIL,
        "total_events": len(body.events),
        "unique_users": len(
            set(e.user for e in body.events)
        ),
        "revenue": revenue,
        "top_user": max(
            totals,
            key=totals.get,
        )
        if totals
        else "",
    }


#############################################
# Q6
#############################################

@app.get("/work")
def work(n: int):

    total = 0

    for i in range(n):
        total += i

    return {
        "email": EMAIL,
        "done": n,
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "uptime_s": time.time() - START_TIME,
    }


@app.get("/logs/tail")
def logs(limit: int = 10):

    return list(LOGS)[-limit:]


@app.get("/metrics")
def metrics():

    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )