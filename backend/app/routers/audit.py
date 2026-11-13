# Author: urumb
"""Starting audits and streaming their progress."""
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.app.schemas.code_file import AuditRequest, AuditResultResponse, CodeFile
from backend.app.services.audit_jobs import (
    cap_file_count,
    run_audit_job,
    run_audit_on_files,
    run_github_audit_job,
    stream_job_events,
)
from backend.app.services.input_processor import (
    process_github_repo,
    process_pasted_code,
    process_uploaded_files,
)
from backend.app.services.job_store import create_job, get_job

logger = logging.getLogger(__name__)
router = APIRouter(tags=["audit"])


@router.post("/audit/stream")
def audit_stream_start(request: AuditRequest, background_tasks: BackgroundTasks) -> dict:
    """Start a GitHub or paste audit in the background and return its job_id."""
    logger.info("Received background audit request — input_type: %s", request.input_type)

    if request.input_type == "github":
        if not request.github_url:
            raise HTTPException(status_code=400, detail="github_url is required")
        # Cloning can take minutes, so it happens inside the background job.
        job_id = create_job(request.github_url.split("github.com/")[-1], input_type="github")
        background_tasks.add_task(run_github_audit_job, job_id, request.github_url, request.depth)
        return {"job_id": job_id}

    code_files = process_pasted_code(request.code, request.language)
    job_id = create_job("Pasted Code", input_type="paste")
    code_files = cap_file_count(code_files, job_id=job_id)
    background_tasks.add_task(run_audit_job, job_id, code_files, request.depth)
    return {"job_id": job_id}


@router.post("/audit/stream/upload")
async def audit_stream_upload_start(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    depth: str = Form("full"),
) -> dict:
    """Start an uploaded-files audit in the background and return its job_id."""
    logger.info("Received background upload audit request — %d file(s)", len(files))
    code_files = await process_uploaded_files(files)

    identifier = code_files[0].path if len(code_files) == 1 else f"{len(code_files)} uploaded files"
    job_id = create_job(identifier, input_type="upload")
    code_files = cap_file_count(code_files, job_id=job_id)
    background_tasks.add_task(run_audit_job, job_id, code_files, depth if depth in ("quick", "full") else "full")
    return {"job_id": job_id}


@router.get("/audit/stream/{job_id}")
async def audit_stream_subscribe(job_id: str) -> StreamingResponse:
    """Subscribe to a running or recently finished job via Server-Sent Events."""
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return StreamingResponse(
        stream_job_events(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _resolve_code_files(request: AuditRequest) -> List[CodeFile]:
    if request.input_type == "github":
        return process_github_repo(request.github_url)
    if request.input_type == "paste":
        return process_pasted_code(request.code, request.language)
    return []


@router.post("/audit", response_model=AuditResultResponse)
def audit_code(request: AuditRequest) -> AuditResultResponse:
    """Run a full audit synchronously (fallback; the UI uses /audit/stream)."""
    logger.info("Received sync audit request — input_type: %s", request.input_type)
    return run_audit_on_files(cap_file_count(_resolve_code_files(request)))


@router.post("/audit/upload", response_model=AuditResultResponse)
async def audit_upload(files: List[UploadFile] = File(...)) -> AuditResultResponse:
    """Run a full audit of uploaded files synchronously."""
    logger.info("Received upload audit request — %d file(s)", len(files))
    return run_audit_on_files(cap_file_count(await process_uploaded_files(files)))
