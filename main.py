from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

API_KEY = "ak_tv28mpb9ju21g5ttd7umz8ce"
EMAIL = "24f1000587@ds.study.iitm.ac.in"   # Replace with your IITM email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsRequest(BaseModel):
    events: List[Event]

@app.post("/analytics")
def analytics(
    body: AnalyticsRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    total_events = len(body.events)

    unique_users = len(set(e.user for e in body.events))

    revenue = sum(e.amount for e in body.events if e.amount > 0)

    totals = {}

    for e in body.events:
        if e.amount > 0:
            totals[e.user] = totals.get(e.user, 0) + e.amount

    top_user = max(totals, key=totals.get) if totals else ""

    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user
    }