# Author: urumb
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from typing import List

import requests
from fastapi import HTTPException, UploadFile

from backend.app.schemas.code_file import CodeFile

logger = logging.getLogger(__name__)

# File extensions to include when scanning repositories
ALLOWED_EXTENSIONS: set[str] = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".cpp",
    ".c", ".h", ".hpp", ".cs", ".go", ".rb", ".php", ".rs", ".kt", ".swift",
}

# Directories to skip when walking a cloned repository
IGNORED_DIRS: set[str] = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    ".idea", ".vscode", "dist", "build",
}

# Safety limits — untrusted, attacker-controlled repositories must not be
# able to exhaust disk/memory/CPU on the auditing host.
MAX_REPO_SIZE_KB = 300_000  # ~300MB, checked via the GitHub API before cloning
MAX_FILE_BYTES = 512_000  # skip individual files over ~500KB (generated/minified/binary)
MAX_FILES_SCANNED = 500  # stop walking after this many matching files, even before the
                          # audit-stage MAX_FILES_PER_AUDIT cap gets a chance to apply

_GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)"
    r"(?:\.git)?(?:/(?:tree|blob)/(?P<ref>[^?#]+))?/?(?:[?#].*)?$"
)


def process_github_repo(url: str) -> List[CodeFile]:
    """Clone a GitHub repository and extract code files.

    Args:
        url: Public GitHub repository URL.

    Returns:
        List of CodeFile objects extracted from the repository.

    Raises:
        HTTPException: If the URL is invalid, the repo is too large, git
            clone fails, or no code files are found.
    """
    match = _GITHUB_URL_RE.match(url.strip())
    if not match:
        logger.error("Invalid GitHub URL attempted: %s", url)
        raise HTTPException(
            status_code=400,
            detail="Only https://github.com/<owner>/<repo> URLs are supported.",
        )
    owner, repo = match.group("owner"), match.group("repo")
    # Normalized URL: users often paste .../tree/main or omit the scheme.
    url = f"https://github.com/{owner}/{repo}"

    _reject_if_repo_too_large(owner, repo)

    tmp_dir = tempfile.mkdtemp(prefix="auditor_")
    try:
        logger.info("Cloning repository: %s", url)
        # GIT_TERMINAL_PROMPT=0: private/nonexistent repos must fail fast
        # instead of hanging while git waits for credentials on stdin.
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", url, tmp_dir],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr)
            raise HTTPException(
                status_code=400,
                detail=(
                    "Failed to clone repository. Make sure it exists and is public "
                    f"(private repositories are not supported). Details: {result.stderr.strip()[-300:]}"
                ),
            )

        code_files: List[CodeFile] = []
        skipped_large = 0
        for root, dirs, files in os.walk(tmp_dir):
            # In-place modification to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for file_name in files:
                if len(code_files) >= MAX_FILES_SCANNED:
                    break

                _, ext = os.path.splitext(file_name)
                if ext.lower() not in ALLOWED_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(abs_path, tmp_dir)

                try:
                    if os.path.getsize(abs_path) > MAX_FILE_BYTES:
                        skipped_large += 1
                        continue
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    code_files.append(CodeFile(path=rel_path, content=content))
                except OSError as read_err:
                    logger.warning("Skipping unreadable file %s: %s", rel_path, read_err)

            if len(code_files) >= MAX_FILES_SCANNED:
                logger.warning("Repository scan capped at %d files: %s", MAX_FILES_SCANNED, url)
                break

        if skipped_large:
            logger.info("Skipped %d file(s) over %d bytes", skipped_large, MAX_FILE_BYTES)

        if not code_files:
            raise HTTPException(
                status_code=400,
                detail="No auditable source files found in this repository.",
            )

        logger.info("Extracted %d code files from repository", len(code_files))
        return code_files

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="git is not installed or not on PATH on the backend host.",
        )
    except subprocess.TimeoutExpired:
        logger.error("git clone timed out for: %s", url)
        raise HTTPException(
            status_code=408,
            detail="Repository clone timed out (120s limit).",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error processing GitHub repo: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing repository: {str(exc)}",
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _reject_if_repo_too_large(owner: str, repo: str) -> None:
    """Best-effort pre-clone size check via the GitHub API.

    Avoids spending clone time/bandwidth/disk on a repository that's clearly
    too large to audit. Fails open (proceeds to clone) on any API error —
    this is a courtesy optimization, not the only safety boundary (the
    --depth 1 clone and post-clone file caps still apply).
    """
    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            timeout=5,
            headers={"Accept": "application/vnd.github+json"},
        )
        if response.status_code == 404:
            raise HTTPException(
                status_code=400,
                detail=f"Repository {owner}/{repo} was not found or is private.",
            )
        if response.status_code == 200:
            size_kb = response.json().get("size", 0)
            if size_kb > MAX_REPO_SIZE_KB:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Repository is too large to audit ({size_kb / 1024:.0f}MB, "
                        f"limit {MAX_REPO_SIZE_KB / 1024:.0f}MB)."
                    ),
                )
    except HTTPException:
        raise
    except requests.RequestException:
        logger.warning("Could not pre-check repository size for %s/%s; proceeding to clone", owner, repo)


MAX_UPLOAD_FILES = 100
MAX_UPLOAD_FILE_BYTES = 1_000_000  # 1MB per file
MAX_UPLOAD_TOTAL_BYTES = 20_000_000  # 20MB combined


def _is_auditable(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in ALLOWED_EXTENSIONS


def _extract_zip(raw_bytes: bytes, zip_name: str) -> List[CodeFile]:
    """Extract auditable source files from a ZIP archive, in memory.

    Entry names are never used as filesystem paths (nothing is written to
    disk), so zip-slip is not a concern; names are only normalized for display.
    Total uncompressed size is bounded to defend against zip bombs.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail=f"{zip_name} is not a valid ZIP archive.")

    extracted: List[CodeFile] = []
    total = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = [p for p in info.filename.replace("\\", "/").split("/") if p not in ("", ".", "..")]
            if not parts or any(p in IGNORED_DIRS for p in parts[:-1]):
                continue
            if not _is_auditable(parts[-1]) or info.file_size > MAX_FILE_BYTES:
                continue
            total += info.file_size
            if total > MAX_UPLOAD_TOTAL_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{zip_name} expands beyond the {MAX_UPLOAD_TOTAL_BYTES // 1_000_000}MB limit.",
                )
            if len(extracted) >= MAX_FILES_SCANNED:
                break
            with archive.open(info) as fh:
                content = fh.read(MAX_FILE_BYTES + 1).decode("utf-8", errors="ignore")
            extracted.append(CodeFile(path="/".join(parts), content=content))
    return extracted


async def process_uploaded_files(files: List[UploadFile]) -> List[CodeFile]:
    """Read uploaded files (source files and/or ZIP archives) into CodeFiles.

    Raises:
        HTTPException: If too many files/too much data are uploaded, a file
            exceeds the size limit, or nothing auditable was found.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files ({len(files)}) — limit is {MAX_UPLOAD_FILES} per upload.",
        )

    code_files: List[CodeFile] = []
    skipped: List[str] = []
    total_bytes = 0
    try:
        for upload in files:
            raw_bytes = await upload.read()
            # Sanitize filename to prevent absolute path or ../ traversal
            file_name = os.path.basename((upload.filename or "").replace("\\", "/")) or "unnamed_file"
            is_zip = file_name.lower().endswith(".zip")

            limit = MAX_UPLOAD_TOTAL_BYTES if is_zip else MAX_UPLOAD_FILE_BYTES
            if len(raw_bytes) > limit:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file_name} exceeds the {limit // 1_000_000}MB per-file limit.",
                )
            total_bytes += len(raw_bytes)
            if total_bytes > MAX_UPLOAD_TOTAL_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Combined upload size exceeds the {MAX_UPLOAD_TOTAL_BYTES // 1_000_000}MB limit.",
                )

            if is_zip:
                code_files.extend(_extract_zip(raw_bytes, file_name))
            elif _is_auditable(file_name):
                content = raw_bytes.decode("utf-8", errors="ignore")
                code_files.append(CodeFile(path=file_name, content=content))
            else:
                skipped.append(file_name)

        if not code_files:
            detail = "No auditable source files found in the upload."
            if skipped:
                detail += f" Unsupported file(s): {', '.join(skipped[:5])}."
            raise HTTPException(status_code=400, detail=detail)

        if skipped:
            logger.info("Skipped %d unsupported upload(s): %s", len(skipped), skipped)
        logger.info("Processed %d uploaded files", len(code_files))
        return code_files

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing uploaded files: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process uploaded files: {str(exc)}",
        )


MAX_PASTE_CHARS = 500_000  # ~500KB of pasted source


_LANGUAGE_FILENAMES = {
    "python": "pasted_input.py", "javascript": "pasted_input.js",
    "typescript": "pasted_input.ts", "java": "pasted_input.java",
}


def process_pasted_code(code: str, language: str | None = None) -> List[CodeFile]:
    """Wrap pasted code into a single CodeFile.

    Args:
        code: Raw pasted code string.

    Returns:
        List containing one CodeFile.

    Raises:
        HTTPException: If the pasted code is empty or exceeds the size limit.
    """
    if not code or not code.strip():
        raise HTTPException(status_code=400, detail="Pasted code is empty.")
    if len(code) > MAX_PASTE_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Pasted code exceeds the {MAX_PASTE_CHARS:,}-character limit.",
        )
    logger.info("Processing pasted code input (%d chars)", len(code))
    filename = _LANGUAGE_FILENAMES.get((language or "python").lower(), "pasted_input.py")
    return [CodeFile(path=filename, content=code)]
