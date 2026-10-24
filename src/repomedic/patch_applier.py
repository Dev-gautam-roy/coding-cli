"""Safe patch application for verified repositories."""

from pathlib import Path
import shutil
import subprocess
import tempfile
from .patch_validator import validate_patch

class PatchApplicationError(RuntimeError):
    """Raised when patch application fails."""
    pass

def apply_patch_git(workspace: Path, patch_text: str, check_only: bool = False) -> bool:
    """Attempt to apply patch using git apply with safe argument arrays."""
    cmd = ["git", "apply", "--whitespace=nowarn"]
    if check_only:
        cmd.append("--check")

    try:
        proc = subprocess.run(
            cmd,
            input=patch_text,
            cwd=workspace,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        if proc.returncode != 0:
            return False
        return True
    except FileNotFoundError:
        return False

def apply_unified_diff_fallback(workspace: Path, patch_text: str) -> None:
    """
    Minimal Python fallback unified diff applier for single/multi-file hunk replacement.
    Handles standard unified diff format (--- a/file, +++ b/file, @@ -start,len +start,len @@).
    """
    # Parse diff into file blocks
    lines = patch_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            # look ahead for +++
            if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                target_str = lines[i + 1][4:].strip()
                if target_str.startswith("b/"):
                    target_str = target_str[2:]
                target_file = workspace / target_str
                i += 2

                # collect hunks for this file
                hunks = []
                current_hunk = []
                while i < len(lines) and not lines[i].startswith("--- "):
                    if lines[i].startswith("@@ "):
                        if current_hunk:
                            hunks.append(current_hunk)
                        current_hunk = [lines[i]]
                    elif current_hunk:
                        current_hunk.append(lines[i])
                    i += 1
                if current_hunk:
                    hunks.append(current_hunk)

                _apply_file_hunks(target_file, hunks)
                continue
        i += 1

def _apply_file_hunks(file_path: Path, hunks: list[list[str]]) -> None:
    if not file_path.exists():
        # New file creation if hunk adds content
        original_lines: list[str] = []
    else:
        original_lines = file_path.read_text(encoding="utf-8").splitlines()

    new_lines = list(original_lines)

    for hunk in hunks:
        old_slice: list[str] = []
        new_slice: list[str] = []
        for line in hunk[1:]:
            if line.startswith("-"):
                old_slice.append(line[1:])
            elif line.startswith("+"):
                new_slice.append(line[1:])
            elif line.startswith(" "):
                old_slice.append(line[1:])
                new_slice.append(line[1:])

        # Find match for old_slice in new_lines
        matched = False
        old_len = len(old_slice)
        for idx in range(len(new_lines) - old_len + 1):
            if new_lines[idx : idx + old_len] == old_slice:
                new_lines[idx : idx + old_len] = new_slice
                matched = True
                break
        if not matched and old_slice:
            raise PatchApplicationError(f"Hunk could not be matched in {file_path.name}")
        elif not matched and not old_slice:
            # File creation or append
            new_lines.extend(new_slice)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def apply_patch_to_workspace(workspace: Path, patch_text: str) -> None:
    """Validate patch targets and apply patch safely to workspace."""
    validate_patch(workspace, patch_text)

    # First try git apply if git repository
    if (workspace / ".git").exists():
        if apply_patch_git(workspace, patch_text, check_only=False):
            return

    # Fallback to pure Python patcher
    try:
        apply_unified_diff_fallback(workspace, patch_text)
    except Exception as exc:
        raise PatchApplicationError(f"Failed to apply patch: {exc}") from exc

def apply_patch_to_disposable_copy(workspace: Path, patch_text: str) -> tempfile.TemporaryDirectory:
    """Create a temporary copy of the workspace, apply patch, and return the directory object."""
    validate_patch(workspace, patch_text)

    temp_dir = tempfile.TemporaryDirectory(prefix="repomedic_workcopy_")
    dest_path = Path(temp_dir.name)

    # Copy files excluding .git and cache
    def ignore_patterns(dir_path: str, names: list[str]) -> set[str]:
        return {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}.intersection(names)

    shutil.copytree(workspace, dest_path, dirs_exist_ok=True, ignore=ignore_patterns)

    # Apply patch in the temporary copy
    try:
        apply_unified_diff_fallback(dest_path, patch_text)
    except Exception as exc:
        temp_dir.cleanup()
        raise PatchApplicationError(f"Failed to apply patch in disposable copy: {exc}") from exc

    return temp_dir
