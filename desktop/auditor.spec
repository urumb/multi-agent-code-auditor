# PyInstaller build for the desktop app.
#
#   cd frontend && npm run build:desktop && cd ..
#   pyinstaller desktop/auditor.spec --noconfirm --distpath build/desktop/dist --workpath build/desktop/work
#
# Output: build/desktop/dist/MultiAgentAuditor/MultiAgentAuditor.exe (a folder,
# not one file: it starts much faster than a self-extracting single exe).
# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from ruff.__main__ import find_ruff_bin

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
UI = os.path.join(ROOT, "frontend", "out")
if not os.path.isfile(os.path.join(UI, "index.html")):
    raise SystemExit("frontend/out is missing: run `npm run build:desktop` in frontend/ first.")

datas = [
    (UI, "frontend_out"),                                  # the built UI
    (os.path.join(ROOT, "rules"), "rules"),                # semgrep rules (used if semgrep is installed)
    *collect_data_files("webview"),                        # WebView2 helper DLLs
    *collect_data_files("bandit"),
    # bandit finds its checks through package entry points: needs metadata.
    *copy_metadata("bandit"),
    *copy_metadata("stevedore"),
    # Versions are part of the result-cache key (backend/app/services/result_cache.py).
    *copy_metadata("ruff"),
    *copy_metadata("langchain-ollama"),
    *copy_metadata("langgraph"),
]

hiddenimports = [
    *collect_submodules("uvicorn"),        # protocols/loops are imported by name
    *collect_submodules("bandit"),         # plugins and formatters load dynamically
    *collect_submodules("backend"),
    *collect_submodules("src"),
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
]

a = Analysis(
    [os.path.join(ROOT, "desktop", "app.py")],
    pathex=[ROOT],
    binaries=[(find_ruff_bin(), "bin")],   # ruff is a native executable
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "chromadb"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MultiAgentAuditor",
    console=False,                         # windowed app, logs go to %LOCALAPPDATA%\MultiAgentAuditor\logs
    disable_windowed_traceback=False,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MultiAgentAuditor")
