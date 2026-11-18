import json
import time

import pytest

from backend.app.services import model_pull


class FakeResponse:
    def __init__(self, lines):
        self._lines = [json.dumps(x).encode() for x in lines]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        yield from self._lines


@pytest.fixture(autouse=True)
def reset_state():
    model_pull._state.update(model=None, status="idle", completed=0, total=0, error=None)
    yield
    model_pull._state.update(model=None, status="idle", completed=0, total=0, error=None)


def _wait_finished():
    for _ in range(100):
        if model_pull.status()["status"] != "pulling":
            return model_pull.status()
        time.sleep(0.02)
    raise AssertionError("pull never finished")


def test_successful_pull_reports_progress(monkeypatch):
    calls = []

    def fake_post(url, json=None, **kw):
        calls.append((url, json))
        return FakeResponse([
            {"status": "pulling manifest"},
            {"status": "downloading", "total": 100, "completed": 40},
            {"status": "downloading", "total": 100, "completed": 100},
            {"status": "success"},
        ])

    monkeypatch.setattr(model_pull.requests, "post", fake_post)
    assert model_pull.start("qwen2.5-coder:3b")["status"] == "pulling"
    final = _wait_finished()
    assert final["status"] == "done" and final["completed"] == final["total"] == 100
    assert calls[0][0].endswith("/api/pull") and calls[0][1]["model"] == "qwen2.5-coder:3b"


def test_failed_pull_reports_error(monkeypatch):
    monkeypatch.setattr(model_pull.requests, "post",
                        lambda *a, **k: FakeResponse([{"error": "pull model manifest: file does not exist"}]))
    model_pull.start("nope:latest")
    final = _wait_finished()
    assert final["status"] == "error" and "does not exist" in final["error"]


@pytest.mark.parametrize("bad", ["", "Qwen", "a b", "../x", "x;rm -rf", "x:y:z", "-flag"])
def test_bad_model_names_rejected(bad):
    with pytest.raises(ValueError):
        model_pull.start(bad)


def test_only_one_download_at_a_time():
    model_pull._state["status"] = "pulling"
    model_pull._state["model"] = "a"
    with pytest.raises(RuntimeError, match="Already downloading"):
        model_pull.start("b")


def test_ollama_down_gives_a_plain_message(monkeypatch):
    def refuse(*a, **k):
        raise model_pull.requests.ConnectionError("HTTPConnectionPool(...) refused")

    monkeypatch.setattr(model_pull.requests, "post", refuse)
    model_pull.start("qwen2.5-coder:3b")
    assert _wait_finished()["error"] == "Can't reach Ollama. Is it running?"
