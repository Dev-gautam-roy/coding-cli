from pathlib import Path
import pytest
from repomedic.patch_validator import (
    InvalidPatchError,
    UnsafePatchPath,
    extract_patch_targets,
    validate_patch,
)

SAMPLE_VALID_PATCH = """--- a/src/calc.py
+++ b/src/calc.py
@@ -1,3 +1,3 @@
 def add(a, b):
-    return a - b
+    return a + b
"""

SAMPLE_TRAVERSAL_PATCH = """--- a/outside.py
+++ b/../outside.py
@@ -1,1 +1,1 @@
-evil
+good
"""

def test_extract_patch_targets():
    targets = extract_patch_targets(SAMPLE_VALID_PATCH)
    assert targets == ["src/calc.py"]

def test_validate_patch_success(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    target = workspace / "src" / "calc.py"
    target.parent.mkdir()
    target.write_text("def add(a, b):\n    return a - b\n")

    validated = validate_patch(workspace, SAMPLE_VALID_PATCH)
    assert len(validated) == 1
    assert validated[0] == target.resolve()

def test_validate_patch_rejects_traversal(tmp_path: Path):
    workspace = tmp_path / "repo"
    workspace.mkdir()

    with pytest.raises(UnsafePatchPath, match="Parent-directory traversal"):
        validate_patch(workspace, SAMPLE_TRAVERSAL_PATCH)

def test_validate_patch_rejects_empty():
    with pytest.raises(InvalidPatchError, match="Patch is empty"):
        validate_patch(Path("."), "")

def test_validate_patch_rejects_missing_hunks(tmp_path: Path):
    bad_patch = "--- a/file.py\n+++ b/file.py\njust text without hunk headers\n"
    with pytest.raises(InvalidPatchError, match="valid unified diff hunks"):
        validate_patch(tmp_path, bad_patch)
