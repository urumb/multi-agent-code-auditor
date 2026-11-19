# Author: urumb
"""Desktop app: the auditor in its own window, fully on this computer.

Starts the backend (which also serves the built UI) on a free localhost
port, then opens it in a native window (pywebview, using Windows' built-in
WebView2). Closing the window stops everything.

    python desktop/app.py                 # run from source (after npm run build:desktop)
    python desktop/app.py --smoke-test    # start, run a tools-only audit, exit (CI)

Packaged with PyInstaller (desktop/auditor.spec) into a folder with
MultiAgentAuditor.exe.
"""
import json
import logging
import multiprocessing
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

if not getattr(sys, "frozen", False):
    # Running from source: make the repo's packages (backend, src) importable.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

APP_NAME = "MultiAgentAuditor"
APP_TITLE = "Multi-Agent Code Auditor"
APP_VERSION = "0.8.0"
FROZEN = getattr(sys, "frozen", False)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
def resource_path(*parts: str) -> Path:
    """A file shipped with the app (PyInstaller unpacks to sys._MEIPASS)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def ui_dir() -> Path:
    bundled = resource_path("frontend_out")
    return bundled if bundled.is_dir() else resource_path("frontend", "out")


def data_dir() -> Path:
    """Where audit history, the cache, logs and window storage live."""
    if os.getenv("DATA_DIR"):
        return Path(os.environ["DATA_DIR"])
    root = os.getenv("LOCALAPPDATA") or os.path.join(Path.home(), ".local", "share")
    return Path(root) / APP_NAME


# ---------------------------------------------------------------------------
# Analyzer subprocesses inside the packaged app
# ---------------------------------------------------------------------------
def run_tool_module(argv: list[str]) -> int:
    """Handle `<app> -m bandit|ruff ...`.

    src/static_analysis.py runs the analyzers as `sys.executable -m <tool>`.
    In the packaged app sys.executable is this program, so it answers those
    calls itself: bandit runs in-process, ruff runs its bundled binary.
    """
    tool, args = argv[0], argv[1:]
    if tool == "bandit":
        from bandit.cli.main import main as bandit_main

        sys.argv = ["bandit", *args]
        try:
            bandit_main()
        except SystemExit as exc:
            return int(exc.code or 0)
        return 0
    if tool == "ruff":
        ruff = resource_path("bin", "ruff.exe" if os.name == "nt" else "ruff")
        return subprocess.run([str(ruff), *args], stdin=subprocess.DEVNULL).returncode
    print(f"unknown tool module: {tool}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def configure_environment(data: Path) -> None:
    """Settings for desktop use. Must run before the backend is imported,
    because src/config.py reads the environment once at import time."""
    data.mkdir(parents=True, exist_ok=True)
    # pywebview resolves its base folder from argv[0] relative to the current
    # folder; make it absolute before changing folders below.
    sys.argv[0] = os.path.abspath(sys.argv[0])
    os.environ.setdefault("DATA_DIR", str(data))
    os.environ["AUTH_ENABLED"] = "false"  # only reachable from this computer
    os.environ.setdefault("AUDITOR_BUILD", APP_VERSION)  # part of the cache key
    # A .env in the data folder can still override settings (e.g. MODEL_NAME).
    os.chdir(data)


def setup_logging(data: Path) -> None:
    logs = data / "logs"
    logs.mkdir(exist_ok=True)
    log_file = open(logs / "app.log", "a", encoding="utf-8", buffering=1)
    # A windowed app has no console: give libraries somewhere to write.
    if sys.stdout is None:
        sys.stdout = log_file
    if sys.stderr is None:
        sys.stderr = log_file
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(log_file)],
        force=True,
    )


def start_server(port: int):
    import uvicorn

    from backend.app.standalone import create_app

    config = uvicorn.Config(
        create_app(ui_dir()), host="127.0.0.1", port=port, log_config=None, access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="auditor-server", daemon=True)
    thread.start()
    return server, thread


def wait_until_up(base: str, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/api/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("The auditor's server didn't start (see logs/app.log).")


# ---------------------------------------------------------------------------
# Smoke test (used in CI on every build)
# ---------------------------------------------------------------------------
SMOKE_CODE = (
    '"""Smoke-test sample: long enough for a full (not "small snippet") plan."""\n'
    "import os\n"
    "import sys\n\n\n"
    "def ping(host):\n"
    "    # bandit B605 (shell command), and ruff F401 (sys unused) above\n"
    "    return os.system('ping -c 1 ' + host)\n"
)


def smoke_test(base: str) -> int:
    """Run one tools-only audit end to end: proves the UI, the API and both
    bundled analyzers (bandit B605, ruff F401) work in this build."""
    page = urllib.request.urlopen(f"{base}/", timeout=10).read().decode()
    if "<html" not in page.lower():
        print("smoke test: UI not served", file=sys.stderr)
        return 1
    body = json.dumps({"input_type": "paste", "language": "python", "depth": "full",
                       "use_cache": False, "code": SMOKE_CODE}).encode()
    req = urllib.request.Request(f"{base}/api/audit/stream", data=body,
                                 headers={"Content-Type": "application/json"})
    job_id = json.load(urllib.request.urlopen(req, timeout=30))["job_id"]
    stream = urllib.request.urlopen(f"{base}/api/audit/stream/{job_id}", timeout=180).read().decode()
    checks = {"bandit (B605)": "B605" in stream, "ruff (F401)": "F401" in stream,
              "audit finished": '"type": "done"' in stream}
    for name, ok in checks.items():
        print(f"smoke test: {name}: {'ok' if ok else 'FAILED'}")
    return 0 if all(checks.values()) else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "-m":
        return run_tool_module(argv[1:])

    data = data_dir()
    configure_environment(data)
    setup_logging(data)
    smoke = "--smoke-test" in argv
    if smoke:
        os.environ["AI_ENABLED"] = "false"  # no Ollama on CI machines

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server, thread = start_server(port)
    try:
        wait_until_up(base)
        if smoke:
            return smoke_test(base)

        import webview

        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.create_window(APP_TITLE, base, width=1320, height=880, min_size=(960, 640))
        # Not private: keeps Settings and the latest result between launches.
        webview.start(private_mode=False, storage_path=str(data / "webview"))
        return 0
    finally:
        server.should_exit = True
        thread.join(timeout=10)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main(sys.argv[1:]))
