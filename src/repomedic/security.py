"""Security policies, path boundary guards, and secret redaction."""

from pathlib import Path
import re

class UnsafePathError(ValueError):
    """Raised when a file path violates security boundary rules."""
    pass

# Common patterns for sensitive files that should never be read or sent to models
EXCLUDED_PATTERNS = {
    r"^\.env(\..+)?$",
    r".*\.pem$",
    r".*\.key$",
    r".*\.p12$",
    r".*\.id_rsa$",
    r".*id_rsa(\..+)?$",
    r".*id_ed25519(\..+)?$",
    r"^\.git(/|\\|$)",
    r"credentials\.json$",
    r"service-account.*\.json$",
}

# Regex to redact potential secrets in logs or code snippets
SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|auth)[\s:=]+(['\"])?([a-zA-Z0-9_\-\.]{16,})(['\"])?"), r"\1=\2[REDACTED_SECRET]\4"),
    (re.compile(r"bearer\s+([a-zA-Z0-9_\-\.]{16,})", re.IGNORECASE), r"Bearer [REDACTED_TOKEN]"),
    (re.compile(r"(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})"), r"[REDACTED_GH_TOKEN]"),
]

def is_path_excluded(relative_path: str | Path) -> bool:
    """Check if relative path matches any sensitive file patterns."""
    path_str = str(relative_path).replace("\\", "/")
    parts = Path(relative_path).parts
    if ".git" in parts or any(p in (".venv", "node_modules", "__pycache__") for p in parts):
        return True
    for pat in EXCLUDED_PATTERNS:
        if re.search(pat, path_str, re.IGNORECASE):
            return True
    return False

def redact_secrets(text: str) -> str:
    """Redact sensitive strings like API keys, tokens, and passwords."""
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted

def validate_workspace_path(workspace: Path, relative_path: str) -> Path:
    """
    Ensure relative_path resolves strictly within workspace and does not escape it.
    Rejects absolute paths, '..' traversal, symlinks, and repository metadata.
    """
    root = workspace.resolve(strict=True)
    raw = Path(relative_path)

    if raw.is_absolute():
        raise UnsafePathError("Absolute paths are not allowed.")

    if ".." in raw.parts:
        raise UnsafePathError("Parent-directory traversal is not allowed.")

    if ".git" in raw.parts:
        raise UnsafePathError("Repository metadata is not a patch target.")

    target = (root / raw).resolve(strict=False)

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("Path escapes the selected workspace.") from exc

    if target.exists() and target.is_symlink():
        raise UnsafePathError("Symlink targets are not supported.")

    return target
