"""Subprocess test runner with argument list enforcement, timeout, and bounded output."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

@dataclass
class TestResult:
    status: str            # "passed", "failed", "timed_out", or "error"
    returncode: int | None
    output: str
    command: list[str]

ALLOWED_PROFILES: dict[str, list[str]] = {
    "pytest": [sys.executable, "-m", "pytest", "-q"],
    "unittest": [sys.executable, "-m", "unittest", "discover", "-v"],
}

def run_test_profile(
    workspace: Path,
    profile: str = "pytest",
    timeout_seconds: int = 60,
    extra_args: list[str] | None = None,
) -> TestResult:
    """
    Safely execute an allowlisted test runner profile inside workspace.
    Uses argument array, shell=False, and strict execution timeout.
    """
    if profile not in ALLOWED_PROFILES:
        raise ValueError(
            f"Unknown test profile '{profile}'. Allowed profiles: {list(ALLOWED_PROFILES.keys())}"
        )

    cmd = list(ALLOWED_PROFILES[profile])
    if extra_args:
        cmd.extend(extra_args)

    try:
        completed = subprocess.run(
            cmd,
            cwd=workspace,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        combined_output = (completed.stdout + "\n" + completed.stderr).strip()
        bounded_output = combined_output[-12000:]
        status = "passed" if completed.returncode == 0 else "failed"
        return TestResult(
            status=status,
            returncode=completed.returncode,
            output=bounded_output,
            command=cmd,
        )
    except subprocess.TimeoutExpired as exc:
        output = ""
        if exc.stdout:
            output += exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode("utf-8", errors="replace")
        if exc.stderr:
            output += exc.stderr if isinstance(exc.stderr, str) else exc.stderr.decode("utf-8", errors="replace")
        return TestResult(
            status="timed_out",
            returncode=None,
            output=(output + "\n[Execution exceeded timeout limits]").strip()[-12000:],
            command=cmd,
        )
    except Exception as exc:
        return TestResult(
            status="error",
            returncode=-1,
            output=f"Error executing test profile: {exc}",
            command=cmd,
        )
