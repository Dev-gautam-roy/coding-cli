"""Unified diff patch validation and workspace confinement."""

from pathlib import Path
import re
from .security import validate_workspace_path, UnsafePathError

class UnsafePatchPath(UnsafePathError):
    """Raised when patch contains dangerous or out-of-workspace file paths."""
    pass

class InvalidPatchError(ValueError):
    """Raised when the patch syntax or hunk structure is malformed."""
    pass

MAX_FILES_PER_PATCH = 10
MAX_PATCH_SIZE_BYTES = 100_000

DIFF_HEADER_RE = re.compile(r"^diff\s+--git\s+a/(.+?)\s+b/(.+?)$", re.MULTILINE)
TARGET_FILE_RE = re.compile(r"^\+\+\+\s+(?:b/)?([^\r\n\t]+)", re.MULTILINE)
HUNK_HEADER_RE = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@")

def extract_patch_targets(patch_text: str) -> list[str]:
    """Extract list of target file paths modified by a unified diff patch."""
    targets = []
    # Match standard '+++ b/path' or '+++ path'
    for match in TARGET_FILE_RE.finditer(patch_text):
        target = match.group(1).strip()
        if target != "/dev/null":
            # Strip standard git prefixes if present
            if target.startswith("b/"):
                target = target[2:]
            if target not in targets:
                targets.append(target)
    return targets

def validate_patch(workspace: Path, patch_text: str) -> list[Path]:
    """
    Validate that patch_text is a well-formed unified diff and targets only safe,
    in-workspace files. Returns list of resolved target Path objects.
    """
    if not patch_text or not patch_text.strip():
        raise InvalidPatchError("Patch is empty.")

    if len(patch_text.encode("utf-8")) > MAX_PATCH_SIZE_BYTES:
        raise InvalidPatchError(f"Patch exceeds maximum allowed size ({MAX_PATCH_SIZE_BYTES} bytes).")

    targets = extract_patch_targets(patch_text)
    if not targets:
        raise InvalidPatchError("No target files found in patch (missing +++ header).")

    if len(targets) > MAX_FILES_PER_PATCH:
        raise InvalidPatchError(
            f"Patch modifies too many files ({len(targets)} > {MAX_FILES_PER_PATCH})."
        )

    # Basic hunk structure check
    has_hunk = False
    for line in patch_text.splitlines():
        if HUNK_HEADER_RE.match(line):
            has_hunk = True
            break
    if not has_hunk:
        raise InvalidPatchError("Patch does not contain any valid unified diff hunks (@@ ... @@).")

    # Validate each target path against workspace security policy
    validated_paths: list[Path] = []
    for rel_path in targets:
        try:
            target_path = validate_workspace_path(workspace, rel_path)
            validated_paths.append(target_path)
        except UnsafePathError as exc:
            raise UnsafePatchPath(f"Unsafe patch target '{rel_path}': {exc}") from exc

    return validated_paths
