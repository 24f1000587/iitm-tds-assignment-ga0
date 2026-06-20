from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SentimentRequest(BaseModel):
    sentences: List[str]

happy_words = {
    "love", "great", "awesome", "happy", "good",
    "excellent", "amazing", "wonderful", "fantastic"
}

sad_words = {
    "sad", "terrible", "bad", "hate", "awful",
    "horrible", "worst", "angry", "upset"
}

def detect_sentiment(sentence: str):
    text = sentence.lower()

    happy_score = sum(word in text for word in happy_words)
    sad_score = sum(word in text for word in sad_words)

    if happy_score > sad_score:
        return "happy"
    elif sad_score > happy_score:
        return "sad"
    else:
        return "neutral"

@app.post("/sentiment")
async def sentiment(data: SentimentRequest):
    results = []

    for sentence in data.sentences:
        results.append({
            "sentence": sentence,
            "sentiment": detect_sentiment(sentence)
        })

    return {"results": results}