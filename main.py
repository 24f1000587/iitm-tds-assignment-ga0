from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from collections import defaultdict

app = FastAPI()

EMAIL = "24f1000587@ds.study.iitm.ac.in"

# ----------------------------
# CORS
# ----------------------------
ALLOWED_ORIGINS = [
    "https://app-wvb82n.example.com",
    # Add the exam origin here if they provide one.
    # Example:
    # "https://exam.example.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Rate Limiter
# ----------------------------
WINDOW = 10  # seconds
LIMIT = 9

client_requests = defaultdict(list)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    timestamps = client_requests[client_id]

    # Remove expired timestamps
    while timestamps and now - timestamps[0] > WINDOW:
        timestamps.pop(0)

    if len(timestamps) >= LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    timestamps.append(now)

    response = await call_next(request)
    return response


# ----------------------------
# Request Context Middleware
# ----------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response


# ----------------------------
# Endpoint
# ----------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }