import asyncio
import io
import zipfile

import pytest
from fastapi import HTTPException, UploadFile

from backend.app.services import input_processor as ip


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=name)


def _zip(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in entries.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_zip_extracts_only_auditable_files():
    data = _zip({"p/a.py": "x=1", "p/readme.txt": "hi", "node_modules/b.py": "y=2"})
    files = asyncio.run(ip.process_uploaded_files([_upload("p.zip", data)]))
    assert [f.path for f in files] == ["p/a.py"]


def test_unsupported_upload_is_rejected():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ip.process_uploaded_files([_upload("notes.txt", b"hi")]))
    assert exc.value.status_code == 400


def test_invalid_zip_is_rejected():
    with pytest.raises(HTTPException):
        asyncio.run(ip.process_uploaded_files([_upload("bad.zip", b"not a zip")]))


def test_paste_uses_language_extension():
    assert ip.process_pasted_code("x", "javascript")[0].path == "pasted_input.js"
    assert ip.process_pasted_code("x")[0].path == "pasted_input.py"


@pytest.mark.parametrize("url", [
    "https://github.com/a/b", "github.com/a/b.git",
    "https://github.com/a/b/tree/main/src", "http://www.github.com/a/b/",
])
def test_github_url_variants_accepted(url):
    assert ip._GITHUB_URL_RE.match(url)


def test_non_github_url_rejected():
    with pytest.raises(HTTPException):
        ip.process_github_repo("https://evil.com/a/b")
