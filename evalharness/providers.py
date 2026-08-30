"""Provider interface for generating LLM outputs.

A provider only needs to implement `generate(prompt: str, **kwargs) -> str`.
This keeps swapping in a real API-backed provider a small, isolated change,
without touching the runner or scorers.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError


class MockProvider(Provider):
    """Deterministic fake provider for offline development and tests.

    Uses a small canned-response table keyed by keywords in the prompt so the
    example suite produces sensible pass/fail results without hitting a real
    API. Falls back to echoing a hash-derived placeholder for unknown prompts,
    which is useful for confirming the harness plumbing works end-to-end.
    """

    name = "mock"

    CANNED = {
        "capital of france": "Paris",
        "primary colors": "red, blue, and yellow",
        "today's date": "2024-01-01",
        "hash map": (
            "A hash map stores key-value pairs and uses a hash function to find "
            "the right slot quickly. This makes looking up a value by its key "
            "very fast on average."
        ),
    }

    def __init__(self, **kwargs):
        # Accept and ignore model/base_url/temperature so the CLI can pass
        # the same kwargs to any provider uniformly.
        pass

    def generate(self, prompt: str, **kwargs) -> str:
        lowered = prompt.lower()
        for key, response in self.CANNED.items():
            if key in lowered:
                return response

        # The judge-grading prompt asks the mock provider to "grade" something.
        # Give it a plausible, deterministic score so llm_rubric tests can run
        # fully offline.
        if "SCORE:" in prompt or "score the" in lowered or "rubric" in lowered:
            digest = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
            score = round((digest % 100) / 100, 2)
            return f"SCORE: {score}\nThe output partially meets the rubric criteria."

        # Deterministic placeholder so repeated runs are reproducible.
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"<mock-response-{digest}>"


class OpenAIProvider(Provider):
    """Provider for any OpenAI-compatible chat-completions HTTP API.

    Reads the API key from the OPENAI_API_KEY environment variable (or an
    explicit `api_key` kwarg). Uses only the standard library for the HTTP
    call to avoid pulling in an extra dependency for a small eval tool.

    Note: this has no retry/backoff logic -- a network error or non-200
    response raises immediately. That's an acceptable tradeoff for a small
    eval harness but is called out here (and in the README) rather than
    pretending it's production-hardened.
    """

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        temperature: float = 0.0,
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError(
                "No API key set. Set OPENAI_API_KEY or pass api_key= explicitly."
            )

        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self.temperature),
        }
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API returned {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to reach {self.base_url}: {e}") from e

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected response shape from API: {data}") from e


PROVIDERS = {
    "mock": MockProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str, **kwargs) -> Provider:
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(PROVIDERS.keys())}"
        )
    return PROVIDERS[name](**kwargs)
