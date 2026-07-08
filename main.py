from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import time
import base64

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows the grader
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Assigned Values
# -----------------------------
TOTAL_ORDERS = 40
RATE_LIMIT = 18
WINDOW = 10  # seconds

# -----------------------------
# In-memory storage
# -----------------------------
idempotency_store = {}

# client_id -> timestamps
rate_limit_store = {}

# Fixed catalog of orders
orders = [
    {
        "id": i,
        "item": f"Item {i}",
        "amount": i * 100
    }
    for i in range(1, TOTAL_ORDERS + 1)
]


# -----------------------------
# Models
# -----------------------------
class OrderCreate(BaseModel):
    item: str = "Sample Item"
    amount: int = 100


# -----------------------------
# Rate Limiter
# -----------------------------
@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client = request.headers.get("X-Client-Id")

    if client:
        now = time.time()

        timestamps = rate_limit_store.get(client, [])

        timestamps = [t for t in timestamps if now - t < WINDOW]

        if len(timestamps) >= RATE_LIMIT:
            retry = WINDOW - (now - timestamps[0])
            retry = max(1, int(retry))

            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={
                    "Retry-After": str(retry)
                }
            )

        timestamps.append(now)
        rate_limit_store[client] = timestamps

    return await call_next(request)


# -----------------------------
# POST /orders
# -----------------------------
@app.post("/orders", status_code=201)
def create_order(
    order: OrderCreate,
    idempotency_key: Optional[str] = Header(None)
):

    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header required"
        )

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    created = {
        "id": str(uuid.uuid4()),
        "item": order.item,
        "amount": order.amount
    }

    idempotency_store[idempotency_key] = created

    return created


# -----------------------------
# Cursor helpers
# -----------------------------
def encode_cursor(index: int):
    return base64.b64encode(str(index).encode()).decode()


def decode_cursor(cursor: Optional[str]):
    if not cursor:
        return 0

    try:
        return int(base64.b64decode(cursor).decode())
    except:
        return 0


# -----------------------------
# GET /orders
# -----------------------------
@app.get("/orders")
def list_orders(limit: int = 10, cursor: Optional[str] = None):

    start = decode_cursor(cursor)

    end = min(start + limit, TOTAL_ORDERS)

    items = orders[start:end]

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = encode_cursor(end)

    return {
        "items": items,
        "next_cursor": next_cursor
    }


@app.get("/")
def root():
    return {"status": "running"}