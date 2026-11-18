import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app.services import db
from backend.app.standalone import create_app
from src.config import Config


@pytest.fixture
def ui_dir(tmp_path):
    (tmp_path / "index.html").write_text("<h1>home</h1>")
    (tmp_path / "404.html").write_text("<h1>not here</h1>")
    (tmp_path / "history" / "view").mkdir(parents=True)
    (tmp_path / "history" / "view" / "index.html").write_text("<h1>detail</h1>")
    seg = tmp_path / "history" / "view" / "__next.history" / "view"
    seg.mkdir(parents=True)
    (seg / "__PAGE__.txt").write_text("prefetch-data")
    return tmp_path


@pytest.fixture
def client(ui_dir, monkeypatch):
    monkeypatch.setattr(Config, "AUDIT_DB_PATH", os.path.join(tempfile.mkdtemp(), "audit.db"))
    monkeypatch.setattr("src.llm.warm_up_model", lambda: None)
    db._initialized = False
    with TestClient(create_app(ui_dir)) as c:
        yield c
    db._initialized = False


def test_ui_and_api_on_one_address(client):
    assert "home" in client.get("/").text
    assert "detail" in client.get("/history/view/?id=abc").text
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/audit/history").status_code == 200  # API startup ran (DB initialised)
    assert client.get("/api/settings").json()["model"]


def test_unknown_page_gets_404_page(client):
    resp = client.get("/no/such/page/")
    assert resp.status_code == 404 and "not here" in resp.text


def test_missing_build_is_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="build:desktop"):
        create_app(tmp_path)


def test_next_segment_prefetch_files_are_found(client):
    # Next asks for dotted names; the export stores them in folders.
    resp = client.get("/history/view/__next.history.view.__PAGE__.txt?_rsc=x")
    assert resp.status_code == 200 and resp.text == "prefetch-data"
    assert client.get("/history/view/__next.nope.__PAGE__.txt").status_code == 404
    # Can't be used to step outside the UI folder.
    assert client.get("/history/view/__next.....secret.__PAGE__.txt").status_code == 404
