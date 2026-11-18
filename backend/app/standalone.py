# Author: urumb
"""One server for UI + API, used by the desktop app.

The static UI (``npm run build:desktop`` → frontend/out) is served at ``/``
and the regular backend app is mounted at ``/api``, the same layout as the
production Caddy setup. Everything is on one address, so there's no CORS
and no second server process.
"""
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.main import app as api_app

# Next.js prefetches page segments as e.g. "history/view/__next.history.view.__PAGE__.txt",
# but the static export stores them as "history/view/__next.history/view/__PAGE__.txt".
_SEGMENT_PREFETCH = re.compile(r"^__next\.(?P<segments>.+)\.(?P<leaf>__PAGE__\.txt)$")


class ExportedSiteFiles(StaticFiles):
    """StaticFiles that also finds Next.js segment-prefetch files."""

    def lookup_path(self, path: str):
        full_path, stat_result = super().lookup_path(path)
        if stat_result is None:
            folder, name = os.path.split(path)
            match = _SEGMENT_PREFETCH.match(name)
            if match:
                first, *rest = match.group("segments").split(".")
                alternative = os.path.join(folder, f"__next.{first}", *rest, match.group("leaf"))
                return super().lookup_path(alternative)
        return full_path, stat_result


def create_app(static_dir: Path) -> FastAPI:
    static_dir = Path(static_dir)
    if not (static_dir / "index.html").is_file():
        raise FileNotFoundError(
            f"No built UI in {static_dir}. Run `npm run build:desktop` in frontend/ first."
        )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        # Starlette doesn't run a mounted sub-app's lifespan, so run the API's
        # startup/shutdown (security check, data migration, DB init) here.
        async with api_app.router.lifespan_context(api_app):
            yield

    root = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    root.mount("/api", api_app)
    # html=True: "/history/view/" serves history/view/index.html, and unknown
    # paths get the exported 404.html.
    root.mount("/", ExportedSiteFiles(directory=static_dir, html=True), name="ui")
    return root
