from pathlib import Path
import pytest
from repomedic.security import (
    UnsafePathError,
    is_path_excluded,
    redact_secrets,
    validate_workspace_path,
)

def test_validate_workspace_path_valid(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    target_file = workspace / "src" / "app.py"
    target_file.parent.mkdir()
    target_file.touch()

    resolved = validate_workspace_path(workspace, "src/app.py")
    assert resolved == target_file.resolve()

def test_validate_workspace_path_rejects_parent_traversal(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()

    with pytest.raises(UnsafePathError, match="Parent-directory traversal"):
        validate_workspace_path(workspace, "../outside.txt")

def test_validate_workspace_path_rejects_absolute_path(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()

    # Absolute path check
    abs_path = str(tmp_path.resolve())
    with pytest.raises(UnsafePathError, match="Absolute paths"):
        validate_workspace_path(workspace, abs_path)

def test_validate_workspace_path_rejects_git_metadata(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()

    with pytest.raises(UnsafePathError, match="Repository metadata"):
        validate_workspace_path(workspace, ".git/config")

def test_is_path_excluded():
    assert is_path_excluded(".env") is True
    assert is_path_excluded(".env.production") is True
    assert is_path_excluded(".git/HEAD") is True
    assert is_path_excluded("id_rsa") is True
    assert is_path_excluded("cert.pem") is True
    assert is_path_excluded("src/utils.py") is False

def test_redact_secrets():
    raw = "api_key='sk-abcdef1234567890abcdef' Bearer ghp_111122223333444455556666777788889999"
    redacted = redact_secrets(raw)
    assert "sk-abcdef1234567890abcdef" not in redacted
    assert "ghp_111122223333444455556666777788889999" not in redacted
    assert "[REDACTED" in redacted
