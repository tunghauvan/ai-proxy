"""Smoke test for chat completions that rely on existing RAG context."""

from __future__ import annotations

import os
import sys
from typing import Sequence

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MODEL = os.getenv("OLLAMA_API_MODEL", "gpt-oss:20b-cloud")


def run_chat_test(query: str, keywords: Sequence[str]) -> bool:
    """Send a chat request and verify the response contains keywords from the KB."""

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Use any knowledge you have access to, including the knowledge base.",
            },
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
    }

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    result = response.json()
    message = result["choices"][0]["message"]["content"].lower()

    matches = [kw for kw in keywords if kw.lower() in message]

    print("Query:", query)
    print("Response snippet:", message[:240].replace("\n", " "))
    print("Keywords found:", matches)

    return len(matches) >= max(1, len(keywords) // 2)


def main() -> bool:
    """Run smoke chat tests against the RAG-aware endpoint."""

    tests = [
        ("What is the maximum document size?", ["100mb", "document size"]),
        ("How does FastAPI expose documentation?", ["openapi", "docs"]),
    ]

    all_passed = True
    for query, keywords in tests:
        try:
            passed = run_chat_test(query, keywords)
        except requests.RequestException as exc:
            print(f"Request failed for '{query}': {exc}")
            passed = False
        if passed:
            print(f"✔ Chat test passed for query: {query}")
        else:
            print(f"✖ Chat test failed for query: {query}")
        all_passed = all_passed and passed

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
