import os
from typing import List

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# Allow the grader's browser to access your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # If your assignment gives a specific origin, replace "*" with it.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Defaults (lowest precedence)
# -----------------------------
config = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


# -----------------------------
# YAML
# -----------------------------
yaml_file = "config.development.yaml"

if os.path.exists(yaml_file):
    with open(yaml_file, "r") as f:
        data = yaml.safe_load(f) or {}
        config.update(data)


# -----------------------------
# .env
# -----------------------------
if os.getenv("APP_PORT") is not None:
    config["port"] = os.getenv("APP_PORT")

if os.getenv("NUM_WORKERS") is not None:
    config["workers"] = os.getenv("NUM_WORKERS")

if os.getenv("APP_LOG_LEVEL") is not None:
    config["log_level"] = os.getenv("APP_LOG_LEVEL")


# -----------------------------
# OS Environment (APP_* only)
# -----------------------------
if os.getenv("APP_DEBUG") is not None:
    config["debug"] = os.getenv("APP_DEBUG")

if os.getenv("APP_API_KEY") is not None:
    config["api_key"] = os.getenv("APP_API_KEY")


# -----------------------------
# Helpers
# -----------------------------
def to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "1", "yes", "on")


def coerce(cfg):
    cfg["port"] = int(cfg["port"])
    cfg["workers"] = int(cfg["workers"])
    cfg["debug"] = to_bool(cfg["debug"])
    cfg["log_level"] = str(cfg["log_level"])
    cfg["api_key"] = "****"
    return cfg


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    result = config.copy()

    # CLI overrides (highest precedence)
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key == "workers":
            result["workers"] = value
        elif key == "port":
            result["port"] = value
        elif key == "debug":
            result["debug"] = value
        elif key == "log_level":
            result["log_level"] = value
        elif key == "api_key":
            result["api_key"] = value
        else:
            result[key] = value

    return coerce(result)


@app.get("/")
def root():
    return {"message": "Config service running"}