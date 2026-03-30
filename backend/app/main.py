# Author: urumb
import json
import logging
from typing import Generator, List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.schemas.code_file import (
    AuditRequest,
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
    description="Phase 4 — Real-time SSE streaming for multi-file audits.",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# SSE Helpers
# ---------------------------------------------------------------------------
def _sse_event(event_type: str, payload: dict) -> str:
    """Format a structured SSE data line.

    Args:
        event_type: One of log, result, file_start, file_done, done, error.
        payload: JSON-serializable dictionary.

    Returns:
        SSE-formatted string ``data: {"type":"...","data":{...}}\\n\\n``.
    """
    return f"data: {json.dumps({'type': event_type, 'data': payload})}\n\n"


def _stream_audit(code_files: List[CodeFile]) -> Generator[str, None, None]:
    """Generator that yields structured SSE events while auditing each file.

    Event types:
        - ``log``: agent activity log entry
        - ``file_start``: a file is about to be processed
        - ``file_done``: a file has finished processing
        - ``result``: per-file audit result
        - ``done``: all files processed
        - ``error``: unhandled exception

    Args:
        code_files: List of CodeFile objects to audit.

    Yields:
        SSE-formatted JSON strings.
    """
    results: List[dict] = []

    try:
        yield _sse_event("log", {
            "agent": "System",
            "message": f"Starting audit — {len(code_files)} file(s) queued",
            "level": "info",
        })

        for i, file in enumerate(code_files, start=1):
            yield _sse_event("file_start", {
                "path": file.path,
                "index": i,
                "total": len(code_files),
            })

            yield _sse_event("log", {
                "agent": "System",
                "message": f"[{i}/{len(code_files)}] Processing: {file.path}",
                "level": "info",
            })

            # Log callback that accumulates agent logs during graph.invoke()
            pending_logs: list[dict] = []

            def log_callback(agent: str, message: str, level: str = "info") -> None:
                pending_logs.append({"agent": agent, "message": message, "level": level})

            try:
                output = run_audit_on_code(file.content, log_callback=log_callback)

                # Yield all accumulated agent logs
                for log_entry in pending_logs:
                    yield _sse_event("log", log_entry)

                file_result = {
                    "file_path": file.path,
                    "final_report": output.get("final_report", ""),
                    "error": None,
                }
                results.append(file_result)

                yield _sse_event("result", file_result)

            except Exception as exc:
                for log_entry in pending_logs:
                    yield _sse_event("log", log_entry)

                file_result = {
                    "file_path": file.path,
                    "final_report": "",
                    "error": str(exc),
                }
                results.append(file_result)

                yield _sse_event("result", file_result)
                yield _sse_event("log", {
                    "agent": "System",
                    "message": f"Failed: {file.path} — {exc}",
                    "level": "error",
                })

            yield _sse_event("file_done", {
                "path": file.path,
                "index": i,
                "total": len(code_files),
            })

        yield _sse_event("done", {"total_files": len(results)})

    except Exception as exc:
        logger.error("Stream failed: %s", exc)
        yield _sse_event("error", {"message": str(exc)})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_code_files(request: AuditRequest) -> List[CodeFile]:
    """Convert an AuditRequest into a list of CodeFile objects.

    Args:
        request: Validated AuditRequest body.

    Returns:
        List of CodeFile objects.
    """
    if request.input_type == "github":
        return process_github_repo(request.github_url)
    elif request.input_type == "paste":
        return process_pasted_code(request.code)
    return []


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
@app.post("/audit/stream")
def audit_stream(request: AuditRequest) -> StreamingResponse:
    """Stream a code audit via Server-Sent Events.

    Accepts the same JSON body as POST /audit. Returns a streaming
    response with SSE events for real-time agent logs and per-file results.

    Args:
        request: Validated AuditRequest body.

    Returns:
        StreamingResponse with media_type text/event-stream.
    """
    logger.info("Received SSE audit request — input_type: %s", request.input_type)
    code_files = _resolve_code_files(request)
    logger.info("Extracted %d file(s), starting SSE stream", len(code_files))

    return StreamingResponse(
        _stream_audit(code_files),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/audit", response_model=AuditResultResponse)
def audit_code(request: AuditRequest) -> AuditResultResponse:
    """Run a full code audit (non-streaming fallback).

    Accepts JSON body with input_type 'github' or 'paste'.
    Converts input into List[CodeFile], runs agents per-file,
    and returns aggregated audit results.

    Args:
        request: Validated AuditRequest body.

    Returns:
        AuditResultResponse with per-file audit reports.
    """
    logger.info("Received audit request — input_type: %s", request.input_type)
    code_files = _resolve_code_files(request)
    logger.info("Extracted %d file(s), starting agent pipeline", len(code_files))
    return _run_audit_on_files(code_files)


@app.post("/audit/upload", response_model=AuditResultResponse)
async def audit_upload(files: List[UploadFile] = File(...)) -> AuditResultResponse:
    """Run a full code audit via file upload.

    Accepts multipart/form-data with one or more files.

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
