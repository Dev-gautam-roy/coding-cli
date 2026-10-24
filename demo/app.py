"""Interactive/automated demo script for RepoMedic CLI."""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

console = Console()

def run_step(title: str, cmd: list[str]):
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]\n[dim]Command: {' '.join(cmd)}[/dim]", expand=False))
    subprocess.run(cmd, check=False)
    console.print()

def main():
    root = Path(__file__).parent.parent
    sample_proj = root / "fixtures" / "broken_sample_project"
    sample_patch = root / "fixtures" / "fix_calculator.patch"

    console.print(Panel.fit("[bold green]RepoMedic CLI End-to-End Demonstration[/bold green]\nNVIDIA Nemotron via Nebius Token Factory", border_style="green"))

    # Step 1: Doctor
    run_step("1. Environment & Pre-flight Diagnostics", [sys.executable, "-m", "repomedic.cli", "doctor"])

    # Step 2: Inspect
    run_step("2. Repository Inspection & Discovery", [sys.executable, "-m", "repomedic.cli", "inspect", str(sample_proj)])

    # Step 3: Baseline test (expected failure)
    run_step("3. Baseline Verification (Expect Failure)", [sys.executable, "-m", "repomedic.cli", "verify", str(sample_proj), "--profile", "pytest"])

    # Step 4: Apply fix patch
    run_step("4. Explicit Human Approval & Patch Application", [sys.executable, "-m", "repomedic.cli", "apply", str(sample_proj), "--patch", str(sample_patch), "--yes"])

    # Step 5: Post-repair verification (expected pass)
    run_step("5. Post-Repair Verification Evidence (Expect Pass)", [sys.executable, "-m", "repomedic.cli", "verify", str(sample_proj), "--profile", "pytest"])

    console.print("[bold green][SUCCESS] Demonstration completed successfully![/bold green]")

if __name__ == "__main__":
    main()
