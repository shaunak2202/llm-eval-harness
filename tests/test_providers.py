import json

import pytest

from evalharness.providers import MockProvider, OpenAIProvider, get_provider


def test_mock_provider_canned_response():
    p = MockProvider()
    assert p.generate("What is the capital of France?") == "Paris"


def test_mock_provider_deterministic_placeholder():
    p = MockProvider()
    out1 = p.generate("some unseen prompt")
    out2 = p.generate("some unseen prompt")
    assert out1 == out2
    assert out1.startswith("<mock-response-")


def test_get_provider_unknown_raises():
    with pytest.raises(ValueError):
        get_provider("not-a-real-provider")


def test_get_provider_mock_ignores_extra_kwargs():
    p = get_provider("mock", model="whatever", base_url="http://x", temperature=0.0)
    assert p.name == "mock"


def test_openai_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    p = OpenAIProvider(api_key=None)
    with pytest.raises(RuntimeError):
        p.generate("hello")


def test_openai_provider_parses_response(monkeypatch):
    p = OpenAIProvider(api_key="fake-key")

    class FakeResp:
        def __init__(self, payload):
            self._payload = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        return FakeResp(
            {"choices": [{"message": {"content": "  Paris  "}}]}
        )

    monkeypatch.setattr("evalharness.providers.urllib.request.urlopen", fake_urlopen)
    result = p.generate("What is the capital of France?")
    assert result == "Paris"
