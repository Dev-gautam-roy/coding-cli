"""Bounded context collection with truncation, redaction, and file-size caps."""

from dataclasses import dataclass, field
from pathlib import Path
from .discovery import discover_repository
from .security import is_path_excluded, redact_secrets

MAX_FILE_SIZE_BYTES = 50_000   # 50 KB max per file
MAX_LOG_SIZE_BYTES = 20_000    # 20 KB max for logs
MAX_TOTAL_FILES = 8

@dataclass
class ContextReport:
    included_files: list[str] = field(default_factory=list)
    omitted_files: list[str] = field(default_factory=list)
    log_included: bool = False
    log_truncated: bool = False
    total_tokens_approx: int = 0

@dataclass
class CollectedContext:
    report: ContextReport
    file_contents: dict[str, str] = field(default_factory=dict)
    error_log: str = ""

def collect_repository_context(
    workspace: Path,
    log_path: Path | None = None,
    specific_files: list[str] | None = None,
) -> CollectedContext:
    """
    Collect bounded source context and optional error log.
    Enforces file-size caps, file count limits, secret redaction, and generates a context report.
    """
    root = workspace.resolve(strict=True)
    report = ContextReport()
    file_contents: dict[str, str] = {}
    error_log = ""

    # Process log if supplied
    if log_path and log_path.is_file():
        try:
            raw_log = log_path.read_text(encoding="utf-8", errors="replace")
            if len(raw_log.encode("utf-8")) > MAX_LOG_SIZE_BYTES:
                raw_log = raw_log[-MAX_LOG_SIZE_BYTES:]
                report.log_truncated = True
            error_log = redact_secrets(raw_log)
            report.log_included = True
        except Exception:
            report.log_included = False

    # Choose files to inspect
    discovery = discover_repository(workspace)
    candidate_files = specific_files if specific_files else discovery.source_files

    included_count = 0
    for rel_path_str in candidate_files:
        rel_path = Path(rel_path_str)
        abs_path = root / rel_path

        if is_path_excluded(rel_path) or not abs_path.is_file():
            report.omitted_files.append(rel_path_str)
            continue

        if included_count >= MAX_TOTAL_FILES:
            report.omitted_files.append(f"{rel_path_str} (exceeded max file limit)")
            continue

        try:
            size = abs_path.stat().st_size
            if size > MAX_FILE_SIZE_BYTES:
                report.omitted_files.append(f"{rel_path_str} (exceeded size cap {MAX_FILE_SIZE_BYTES} bytes)")
                continue

            content = abs_path.read_text(encoding="utf-8", errors="replace")
            content = redact_secrets(content)
            file_contents[rel_path_str] = content
            report.included_files.append(rel_path_str)
            included_count += 1
        except Exception as exc:
            report.omitted_files.append(f"{rel_path_str} (read error: {exc})")

    # Approx token count (~4 chars per token)
    total_chars = sum(len(c) for c in file_contents.values()) + len(error_log)
    report.total_tokens_approx = total_chars // 4

    return CollectedContext(
        report=report,
        file_contents=file_contents,
        error_log=error_log,
    )
