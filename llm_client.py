# -*- coding: utf-8 -*-
"""Shared Groq (OpenAI-compatible) chat client for the LLM features
(explain.py, event_classifier.py, chat_agent.py). Plain HTTPS, no SDK.

Centralizes the call + retry-on-429 + JSON parsing so each feature doesn't
re-implement it. Needs GROQ_API_KEY in .env. Default model: llama-3.3-70b.

Smoke test:  py -3 -X utf8 llm_client.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


class LLMError(RuntimeError):
    pass


def chat(messages, model=DEFAULT_MODEL, temperature=0.2, json_mode=False, max_retries=6):
    """POST a chat-completion to Groq and return the assistant text.

    Retries with backoff on 429 (free-tier rate limit).
    """
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise LLMError("GROQ_API_KEY not set — add it to .env")
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    for attempt in range(max_retries):
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 429:
            time.sleep(min(float(resp.headers.get("retry-after", 2 ** attempt)), 30))
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    raise LLMError("Groq rate limit: exhausted retries")


def chat_json(messages, **kwargs):
    """Like chat() but forces JSON mode and parses to a dict (tolerant of prose)."""
    text = chat(messages, json_mode=True, **kwargs)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    out = chat([{"role": "user", "content": "ענה במילה אחת בלבד: שלום"}])
    print("smoke test OK →", out.strip())
