import pytest
from repomedic.diagnosis import (
    Diagnosis,
    parse_and_validate_diagnosis,
)

SAMPLE_VALID_JSON = """
{
  "summary": "Fix inverted subtraction sign in add function",
  "evidence": ["test_core.py failed with AssertionError: expected 4, got 0"],
  "likely_root_cause": "Typo in core.py where addition used minus operator",
  "proposed_files": ["src/calculator/core.py"],
  "patch": "--- a/src/calculator/core.py\\n+++ b/src/calculator/core.py\\n@@ -1,2 +1,2 @@\\n def add(a, b):\\n-    return a - b\\n+    return a + b",
  "verification_steps": ["pytest -q tests/test_core.py"],
  "limitations": ["Only handles two numbers"]
}
"""

def test_parse_and_validate_diagnosis_success():
    diag = parse_and_validate_diagnosis(SAMPLE_VALID_JSON)
    assert isinstance(diag, Diagnosis)
    assert diag.proposed_files == ["src/calculator/core.py"]
    assert "add" in diag.patch

def test_parse_and_validate_diagnosis_with_code_block():
    wrapped = f"```json\n{SAMPLE_VALID_JSON}\n```"
    diag = parse_and_validate_diagnosis(wrapped)
    assert isinstance(diag, Diagnosis)
    assert diag.summary == "Fix inverted subtraction sign in add function"

def test_parse_and_validate_diagnosis_invalid_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_and_validate_diagnosis("not a json string at all")

def test_parse_and_validate_diagnosis_missing_required_fields():
    with pytest.raises(ValueError, match="failed schema validation"):
        parse_and_validate_diagnosis('{"summary": "Incomplete"}')
