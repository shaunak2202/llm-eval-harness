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


def test_openai_provider_retries_on_429_then_succeeds(monkeypatch):
    import urllib.error

    sleeps = []
    p = OpenAIProvider(api_key="fake-key", retries=3, backoff_base=0.01, sleep_fn=lambda s: sleeps.append(s))

    class FakeResp:
        def __init__(self, payload):
            self._payload = json.dumps(payload).encode("utf-8")

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    calls = {"n": 0}

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(req.full_url, 429, "rate limited", hdrs=None, fp=None)
        return FakeResp({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("evalharness.providers.urllib.request.urlopen", fake_urlopen)
    result = p.generate("hello")
    assert result == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2  # slept before 2nd and 3rd attempts


def test_openai_provider_gives_up_after_max_retries(monkeypatch):
    import urllib.error

    p = OpenAIProvider(api_key="fake-key", retries=2, backoff_base=0.01, sleep_fn=lambda s: None)

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "unavailable", hdrs=None, fp=None)

    monkeypatch.setattr("evalharness.providers.urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="failed after 2 attempts"):
        p.generate("hello")


def test_openai_provider_does_not_retry_on_401(monkeypatch):
    import urllib.error

    calls = {"n": 0}
    p = OpenAIProvider(api_key="fake-key", retries=3, backoff_base=0.01, sleep_fn=lambda s: None)

    def fake_urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 401, "unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr("evalharness.providers.urllib.request.urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="returned 401"):
        p.generate("hello")
    assert calls["n"] == 1  # no retries on non-transient 4xx
