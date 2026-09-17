from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def _load_env() -> None:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


_load_env()

MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "ollama").strip().lower()
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3.5:latest").strip()
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("API_KEY", "").strip()


def _call_ollama(prompt: str, *, format: str | None = None, timeout: int = 15, model: str | None = None) -> str:
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload: dict = {
        "model": model or MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    if format:
        payload["format"] = format

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def _call_api(prompt: str, *, format: str | None = None, timeout: int = 15, model: str | None = None) -> str:
    if not API_BASE_URL:
        raise RuntimeError("API_BASE_URL is required when MODEL_PROVIDER=api")
    if not API_KEY:
        raise RuntimeError("API_KEY is required when MODEL_PROVIDER=api")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "user", "content": prompt}]
    payload: dict = {
        "model": model or MODEL_NAME,
        "messages": messages,
    }
    if format == "json":
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        f"{API_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise TypeError("Expected string response from API provider")
    return content


def call_model(
    prompt: str,
    *,
    format: str | None = None,
    timeout: int = 15,
    model_provider: str | None = None,
    model_name: str | None = None,
) -> str:
    """
    Call the configured model. Optionally override provider/model for this call.
    """
    provider = (model_provider or MODEL_PROVIDER).strip().lower()
    
    if provider == "api":
        return _call_api(prompt, format=format, timeout=timeout, model=model_name)

    return _call_ollama(prompt, format=format, timeout=timeout, model=model_name)
