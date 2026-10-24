from pathlib import Path
import pytest
from repomedic.test_runner import run_test_profile

def test_run_test_profile_disallowed_profile(tmp_path: Path):
    with pytest.raises(ValueError, match="Unknown test profile"):
        run_test_profile(tmp_path, profile="rm_rf")

def test_run_test_profile_basic_pytest(tmp_path: Path):
    # Create a passing dummy test in tmp_path
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_dummy():\n    assert True\n")

    result = run_test_profile(tmp_path, profile="pytest")
    assert result.status == "passed"
    assert result.returncode == 0
    assert "1 passed" in result.output or "passed" in result.output

def test_run_test_profile_failing_pytest(tmp_path: Path):
    # Create a failing test in tmp_path
    test_file = tmp_path / "test_fail.py"
    test_file.write_text("def test_broken():\n    assert 1 == 2\n")

    result = run_test_profile(tmp_path, profile="pytest")
    assert result.status == "failed"
    assert result.returncode != 0
    assert "failed" in result.output
