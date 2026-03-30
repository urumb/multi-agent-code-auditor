# Author: urumb
import logging
import os
import shutil
import subprocess
import tempfile
from typing import List

from fastapi import HTTPException, UploadFile

from backend.app.schemas.code_file import CodeFile

logger = logging.getLogger(__name__)

# File extensions to include when scanning repositories
ALLOWED_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".tsx", ".java", ".cpp", ".go",
}

# Directories to skip when walking a cloned repository
IGNORED_DIRS: set[str] = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    ".idea", ".vscode", "dist", "build",
}


def process_github_repo(url: str) -> List[CodeFile]:
    """Clone a GitHub repository and extract code files.

    Args:
        url: Public GitHub repository URL.

    Returns:
        List of CodeFile objects extracted from the repository.

    Raises:
        HTTPException: If git clone fails or no code files are found.
    """
    if not url.startswith("https://github.com/"):
        logger.error("Invalid GitHub URL attempted: %s", url)
        raise HTTPException(
            status_code=400,
            detail="Only valid https://github.com/ URLs are supported.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="auditor_")
    try:
        logger.info("Cloning repository: %s", url)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, tmp_dir],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr)
            raise HTTPException(
                status_code=400,
                detail=f"Failed to clone repository: {result.stderr.strip()}",
            )

        code_files: List[CodeFile] = []
        for root, dirs, files in os.walk(tmp_dir):
            # In-place modification to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            for file_name in files:
                _, ext = os.path.splitext(file_name)
                if ext.lower() not in ALLOWED_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(abs_path, tmp_dir)

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    code_files.append(CodeFile(path=rel_path, content=content))
                except OSError as read_err:
                    logger.warning("Skipping unreadable file %s: %s", rel_path, read_err)

        logger.info("Extracted %d code files from repository", len(code_files))
        return code_files

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


async def process_uploaded_files(files: List[UploadFile]) -> List[CodeFile]:
    """Read uploaded files and convert them to CodeFile objects.

    Args:
        files: List of FastAPI UploadFile objects.

    Returns:
        List of CodeFile objects.

    Raises:
        HTTPException: If file reading fails or file is > 1MB.
    """
    code_files: List[CodeFile] = []
    try:
        for upload in files:
            raw_bytes = await upload.read()
            if len(raw_bytes) > 1_000_000:
                logger.error("File exceeds 1MB limit: %s", upload.filename)
                raise HTTPException(status_code=400, detail=f"{upload.filename} exceeds 1MB limit.")

            content = raw_bytes.decode("utf-8", errors="ignore")
            # Sanitize filename to prevent absolute math or ../ traversal
            file_name = os.path.basename(upload.filename) if upload.filename else "unnamed_file"
            if not file_name:
                file_name = "unnamed_file"

            code_files.append(CodeFile(path=file_name, content=content))
            logger.info("Processed uploaded file: %s", file_name)

        logger.info("Processed %d uploaded files", len(code_files))
        return code_files

    except Exception as exc:
        logger.error("Error processing uploaded files: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process uploaded files: {str(exc)}",
        )


def process_pasted_code(code: str) -> List[CodeFile]:
    """Wrap pasted code into a single CodeFile.

    Args:
        code: Raw pasted code string.

    Returns:
        List containing one CodeFile.
    """
    logger.info("Processing pasted code input (%d chars)", len(code))
    return [CodeFile(path="pasted_input.py", content=code)]
