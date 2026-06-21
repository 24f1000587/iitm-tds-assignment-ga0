from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
import sys
from io import StringIO
import traceback
import re
import os

load_dotenv()
# Gemini / AI Pipe
from google import genai
from google.genai import types


# =====================================================
# FastAPI App
# =====================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# Request / Response Models
# =====================================================
class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    error: List[int]
    result: str


class ErrorAnalysis(BaseModel):
    error_lines: List[int]


# =====================================================
# Part 1: Execute Python Code
# =====================================================
def execute_python_code(code: str) -> dict:
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)
        output = sys.stdout.getvalue()

        return {
            "success": True,
            "output": output
        }

    except Exception:
        output = traceback.format_exc()

        return {
            "success": False,
            "output": output
        }

    finally:
        sys.stdout = old_stdout


# =====================================================
# Extract line number from traceback (faster than AI)
# =====================================================
def extract_line_from_traceback(trace: str) -> List[int]:
    matches = re.findall(r'line (\d+)', trace)

    if matches:
        return [int(matches[-1])]

    return []


# =====================================================
# Part 2: AI Error Analysis
# =====================================================
def analyze_error_with_ai(code: str, tb: str) -> List[int]:
    client = genai.Client(
    api_key=os.getenv("AIPIPE_TOKEN"),
    http_options={
        "base_url": "https://aipipe.org/openai/v1"
    }
)

    prompt = f"""
Analyze the following Python code and traceback.

Find the exact line number(s) where the error occurred.

CODE:
{code}

TRACEBACK:
{tb}

Return only line numbers.
"""

    response = client.models.generate_content(
        model="openai/gpt-4.1-nano",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "error_lines": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.INTEGER)
                    )
                },
                required=["error_lines"]
            )
        )
    )

    result = ErrorAnalysis.model_validate_json(response.text)
    return result.error_lines


# =====================================================
# API Endpoint
# =====================================================
@app.post("/code-interpreter", response_model=CodeResponse)
def code_interpreter(request: CodeRequest):
    execution = execute_python_code(request.code)

    # If success, no AI needed
    if execution["success"]:
        return {
            "error": [],
            "result": execution["output"]
        }

    traceback_output = execution["output"]

    # Try regex first
    error_lines = extract_line_from_traceback(traceback_output)

    # Use AI only if regex fails
    if not error_lines:
        error_lines = analyze_error_with_ai(
            request.code,
            traceback_output
        )

    return {
        "error": error_lines,
        "result": traceback_output
    }


# =====================================================
# Health Check
# =====================================================
@app.get("/")
def root():
    return {"message": "Code Interpreter API Running"}