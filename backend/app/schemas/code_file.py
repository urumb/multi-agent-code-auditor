# Author: urumb
from typing import List, Literal, Optional


from pydantic import BaseModel, model_validator


class CodeFile(BaseModel):
    """Unified representation of a single code file for audit processing.

    Attributes:
        path: Relative file path or identifier (e.g., 'src/utils.py').
        content: Full text content of the file.
    """

    path: str
    content: str


class AuditRequest(BaseModel):
    """Request body for the POST /audit endpoint (JSON — github/paste inputs).

    Attributes:
        input_type: One of 'github' or 'paste'.
        github_url: Required when input_type is 'github'.
        code: Required when input_type is 'paste'.
    """

    input_type: Literal["github", "paste"]
    github_url: Optional[str] = None
    code: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields_for_input_type(self) -> "AuditRequest":
        """Ensures the correct field is populated based on input_type."""
        if self.input_type == "github" and not self.github_url:
            raise ValueError("github_url is required when input_type is 'github'")
        if self.input_type == "paste" and not self.code:
            raise ValueError("code is required when input_type is 'paste'")
        return self


class AuditResponse(BaseModel):
    """Standard response for audit input processing.

    Attributes:
        message: Human-readable status message.
        file_count: Number of code files extracted.
        files: List of processed CodeFile objects.
    """

    message: str
    file_count: int
    files: List[CodeFile]


class FileAuditResult(BaseModel):
    """Result of auditing a single file.

    Attributes:
        file_path: Path or identifier of the audited file.
        final_report: Markdown audit report (empty string if error).
        error: Error message if the audit failed for this file.
    """

    file_path: str
    final_report: str = ""
    error: Optional[str] = None


class AuditResultResponse(BaseModel):
    """Aggregated response for multi-file audit execution.

    Attributes:
        total_files: Number of files that were audited.
        results: Per-file audit results.
    """

    total_files: int
    results: List[FileAuditResult]
