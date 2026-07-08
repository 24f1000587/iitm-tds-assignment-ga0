from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from collections import defaultdict, deque
import time

app = FastAPI()

EMAIL = "24f1000587@ds.study.iitm.ac.in"  # <-- Replace with your IITM email

# -------------------------------
# CORS
# -------------------------------
ALLOWED_ORIGINS = [
    "https://app-wvb82n.example.com",

    # Add the TDS exam page origin if required
    # Example:
    "https://exam.sanand.workers.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Rate Limiter
# -------------------------------
LIMIT = 9
WINDOW = 10  # seconds

client_buckets = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()

    bucket = client_buckets[client_id]

    while bucket and now - bucket[0] >= WINDOW:
        bucket.popleft()

    if len(bucket) >= LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    bucket.append(now)

    response = await call_next(request)
    return response


# -------------------------------
# Request Context
# -------------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    # Echo the request ID in the response header
    response.headers["X-Request-ID"] = request_id

    return response


# -------------------------------
# Endpoint
# -------------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


# Optional root endpoint
@app.get("/")
async def root():
    return {"status": "ok"}