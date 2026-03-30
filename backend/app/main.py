# Author: urumb
import logging
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.schemas.code_file import (
    AuditRequest,
    AuditResponse,
    AuditResultResponse,
    CodeFile,
    FileAuditResult,
)
from backend.app.services.audit_runner import run_audit_on_code
from backend.app.services.input_processor import (
    process_github_repo,
    process_pasted_code,
    process_uploaded_files,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Multi-Agent Code Auditor",
    description="Phase 2 — Multi-file audit via LangGraph agent pipeline.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _run_audit_on_files(code_files: List[CodeFile]) -> AuditResultResponse:
    """Run the LangGraph audit pipeline on each file and aggregate results.

    Args:
        code_files: List of CodeFile objects to audit.

    Returns:
        AuditResultResponse with per-file results.
    """
    results: List[FileAuditResult] = []

    for file in code_files:
        logger.info("[AUDIT] Processing: %s", file.path)
        try:
            output = run_audit_on_code(file.content)
            results.append(FileAuditResult(
                file_path=file.path,
                final_report=output.get("final_report", ""),
            ))
        except Exception as exc:
            logger.error("[AUDIT] Failed for %s: %s", file.path, exc)
            results.append(FileAuditResult(
                file_path=file.path,
                error=str(exc),
            ))

    logger.info("[AUDIT] Completed — %d file(s) processed", len(results))

    return AuditResultResponse(
        total_files=len(results),
        results=results,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/audit", response_model=AuditResultResponse)
def audit_code(request: AuditRequest) -> AuditResultResponse:
    """Run a full code audit (GitHub URL or pasted code).

    Accepts JSON body with input_type 'github' or 'paste'.
    Converts input into List[CodeFile], runs agents per-file,
    and returns aggregated audit results.

    Args:
        request: Validated AuditRequest body.

    Returns:
        AuditResultResponse with per-file audit reports.
    """
    logger.info("Received audit request — input_type: %s", request.input_type)

    code_files: List[CodeFile] = []

    if request.input_type == "github":
        code_files = process_github_repo(request.github_url)
    elif request.input_type == "paste":
        code_files = process_pasted_code(request.code)

    logger.info("Extracted %d file(s), starting agent pipeline", len(code_files))

    return _run_audit_on_files(code_files)


@app.post("/audit/upload", response_model=AuditResultResponse)
async def audit_upload(files: List[UploadFile] = File(...)) -> AuditResultResponse:
    """Run a full code audit via file upload.

    Accepts multipart/form-data with one or more files.
    Reads files, runs agents per-file, and returns aggregated results.

    Args:
        files: List of uploaded files.

    Returns:
        AuditResultResponse with per-file audit reports.
    """
    logger.info("Received upload audit request — %d file(s)", len(files))

    code_files = await process_uploaded_files(files)

    logger.info("Extracted %d file(s), starting agent pipeline", len(code_files))

    return _run_audit_on_files(code_files)


@app.get("/health")
def health_check() -> dict:
    """Basic health check endpoint.

    Returns:
        Dict with status 'ok'.
    """
    return {"status": "ok"}
