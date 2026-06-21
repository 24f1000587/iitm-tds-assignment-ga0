from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import csv
from typing import List, Optional

app = FastAPI()

# Enable CORS for GET requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Load CSV once when server starts
students_data = []

with open("students.csv", "r", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    for row in reader:
        students_data.append({
            "studentId": int(row["studentId"]),
            "class": row["class"]
        })


@app.get("/api")
async def get_students(class_: Optional[List[str]] = Query(None, alias="class")):
    if class_:
        filtered = [s for s in students_data if s["class"] in class_]
        return {"students": filtered}

    return {"students": students_data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)