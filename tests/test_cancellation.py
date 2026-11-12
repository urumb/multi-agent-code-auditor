import threading
import time

import pytest

from src import llm
from src.agents.security import SecurityAgent
from src.llm import AuditCancelled, invoke_llm


class _FakeChain:
    def __init__(self, delay: float = 0.0):
        self.calls = 0
        self.delay = delay

    def invoke(self, inputs):
        self.calls += 1
        time.sleep(self.delay)
        return type("Resp", (), {"content": '{"findings": []}'})()


def test_cancelled_call_never_reaches_model():
    cancel = threading.Event()
    cancel.set()
    chain = _FakeChain()
    with pytest.raises(AuditCancelled):
        invoke_llm(chain, {}, cancel)
    assert chain.calls == 0


def test_slot_is_released_after_cancel_and_error():
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(AuditCancelled):
        invoke_llm(_FakeChain(), {}, cancel)
    # If the slot leaked, this would block forever.
    assert invoke_llm(_FakeChain(), {}).content == '{"findings": []}'


def test_waiting_call_gives_up_when_cancelled(monkeypatch):
    monkeypatch.setattr(llm, "_LLM_SLOTS", threading.BoundedSemaphore(1))
    llm._LLM_SLOTS.acquire()  # another file's call holds the only slot
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    start = time.time()
    try:
        with pytest.raises(AuditCancelled):
            invoke_llm(_FakeChain(), {}, cancel)
    finally:
        llm._LLM_SLOTS.release()
    assert time.time() - start < 2


def test_agent_stops_remaining_snippets_once_cancelled(monkeypatch):
    agent = SecurityAgent()
    cancel = threading.Event()
    chain = _FakeChain()

    def fake_get_llm():
        return object()

    monkeypatch.setattr(agent, "_get_llm", fake_get_llm)
    monkeypatch.setattr(type(agent.prompt), "__or__", lambda self, other: chain)

    original_invoke = chain.invoke

    def invoke_then_cancel(inputs):
        result = original_invoke(inputs)
        cancel.set()  # timeout fires during the first snippet
        return result

    chain.invoke = invoke_then_cancel

    state = {"code_snippets": ["a", "b", "c"], "cancel_event": cancel}
    with pytest.raises(AuditCancelled):
        agent.run(state)
    assert chain.calls == 1
