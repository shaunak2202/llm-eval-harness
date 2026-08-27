"""Provider interface for generating LLM outputs.

A provider only needs to implement `generate(prompt: str, **kwargs) -> str`.
This keeps swapping in a real API-backed provider a small, isolated change
later on, without touching the runner or scorers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib


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
    }

    def generate(self, prompt: str, **kwargs) -> str:
        lowered = prompt.lower()
        for key, response in self.CANNED.items():
            if key in lowered:
                return response
        # Deterministic placeholder so repeated runs are reproducible.
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return f"<mock-response-{digest}>"


PROVIDERS = {
    "mock": MockProvider,
}


def get_provider(name: str) -> Provider:
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(PROVIDERS.keys())}"
        )
    return PROVIDERS[name]()
