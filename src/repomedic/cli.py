"""Command-line interface for RepoMedic CLI."""

import json
from pathlib import Path
import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from .config import load_settings
from .context import collect_repository_context
from .diagnosis import (
    SYSTEM_PROMPT,
    Diagnosis,
    build_diagnosis_prompt,
    parse_and_validate_diagnosis,
)
from .discovery import discover_repository
from .model_client import ask_model
from .patch_applier import apply_patch_to_disposable_copy, apply_patch_to_workspace
from .patch_validator import validate_patch
from .test_runner import run_test_profile

app = typer.Typer(
    name="repomedic",
    help="RepoMedic: A Safe, Evidence-Based Terminal Agent for Repository Diagnosis and Verified Repair",
    invoke_without_command=True,
)
console = Console()

@app.callback()
def main(
    ctx: typer.Context,
    path: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory to operate on",
        exists=True,
        file_okay=False,
    ),
):
    """
    RepoMedic CLI: Interactive Claude Code style coding agent or single-command subroutines.
    Running `repomedic` with no arguments launches the interactive Claude Code interface!
    """
    if ctx.invoked_subcommand is None:
        from .claude_cli import run_claude_cli
        run_claude_cli(path)

@app.command()
def doctor():
    """Verify local setup, Python version, git availability, and AI model provider configuration."""
    console.print(Panel("[bold cyan]RepoMedic Environment Doctor[/bold cyan]", expand=False))
    table = Table(title="System & Configuration Check")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    table.add_row(
        "Python Runtime",
        "[green]OK[/green]" if py_ok else "[red]FAIL[/red]",
        f"Python {py_ver} ({'Supported' if py_ok else 'Requires >= 3.11'})",
    )

    # Git
    import shutil
    git_bin = shutil.which("git")
    table.add_row(
        "Git Executable",
        "[green]OK[/green]" if git_bin else "[yellow]NOT FOUND[/yellow]",
        str(git_bin or "Not in PATH; pure-Python patcher fallback will be used"),
    )

    # Provider config
    try:
        settings = load_settings()
        table.add_row("Detected Provider", "[green]OK[/green]", settings.provider)
        table.add_row(
            "API Key",
            "[green]CONFIGURED[/green]",
            f"Key: {settings.masked_api_key()}",
        )
        table.add_row("Base URL", "[green]OK[/green]", settings.base_url)
        table.add_row("Configured Model", "[green]OK[/green]", settings.model)
    except Exception as exc:
        table.add_row("AI Provider Config", "[red]MISSING/INVALID[/red]", str(exc))

    console.print(table)

@app.command()
def inspect(
    path: Path = typer.Argument(
        Path("."),
        help="Path to repository to inspect",
        exists=True,
        file_okay=False,
    )
):
    """Inspect repository structure, manifests, and candidate source files."""
    root = path.resolve()
    result = discover_repository(root)

    console.print(Panel(f"[bold]Inspecting Repository:[/bold] {root}", title="RepoMedic Inspect"))

    summary_table = Table(show_header=False)
    summary_table.add_column("Key", style="bold cyan")
    summary_table.add_column("Value")
    summary_table.add_row("Detected Project Type", result.project_type.upper())
    summary_table.add_row("Manifests Found", ", ".join(result.manifests) if result.manifests else "[yellow]None[/yellow]")
    summary_table.add_row("Candidate Source Files", str(len(result.source_files)))
    console.print(summary_table)

    if result.source_files:
        console.print("\n[bold]Sample Candidate Files:[/bold]")
        for f in result.source_files[:10]:
            console.print(f"  * {f}")
        if len(result.source_files) > 10:
            console.print(f"  ... and {len(result.source_files) - 10} more.")

@app.command()
def diagnose(
    path: Path = typer.Argument(
        Path("."),
        help="Path to repository to diagnose",
        exists=True,
        file_okay=False,
    ),
    log: Path = typer.Option(
        None,
        "--log",
        "-l",
        help="Path to test output or error log file",
        exists=True,
        dir_okay=False,
    ),
    output_json: Path = typer.Option(
        None,
        "--out",
        "-o",
        help="Save structured diagnosis JSON to this path",
    ),
):
    """Analyze repository and error logs with configured AI model to generate a structured diagnosis."""
    root = path.resolve()
    console.print(f"[bold cyan]Collecting bounded context for:[/bold cyan] {root}")

    context = collect_repository_context(root, log_path=log)

    console.print(f"  [+] Files included: {len(context.report.included_files)}")
    if context.report.omitted_files:
        console.print(f"  [i] Files omitted/excluded: {len(context.report.omitted_files)}")
    if context.report.log_included:
        console.print(f"  [+] Error log included (approx {context.report.total_tokens_approx} context tokens)")

    settings = load_settings()
    console.print(f"\n[bold green]Calling {settings.provider} ({settings.model})...[/bold green]")

    user_prompt = build_diagnosis_prompt(context)
    raw_response = ask_model(settings, SYSTEM_PROMPT, user_prompt)

    try:
        diag = parse_and_validate_diagnosis(raw_response)
    except Exception as exc:
        console.print(f"[bold red]Validation error on model response:[/bold red] {exc}")
        raise typer.Exit(code=1)

    # Display report
    console.print(Panel(diag.summary, title="Diagnosis Summary", border_style="cyan"))

    console.print("[bold]Evidence:[/bold]")
    for ev in diag.evidence:
        console.print(f"  * {ev}")

    console.print(f"\n[bold]Likely Root Cause:[/bold] {diag.likely_root_cause}")
    console.print(f"[bold]Target Files:[/bold] {', '.join(diag.proposed_files)}")

    console.print("\n[bold]Proposed Patch:[/bold]")
    syntax = Syntax(diag.patch, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(diag.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\n[green]Saved diagnosis to {output_json}[/green]")

@app.command()
def apply(
    path: Path = typer.Argument(
        Path("."),
        help="Path to target repository",
        exists=True,
        file_okay=False,
    ),
    patch_file: Path = typer.Option(
        ...,
        "--patch",
        "-p",
        help="Path to unified diff patch file",
        exists=True,
        dir_okay=False,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip interactive confirmation (use with caution)",
    ),
):
    """Safely validate and apply an approved patch to the repository."""
    root = path.resolve()
    patch_text = patch_file.read_text(encoding="utf-8")

    # Validate patch against security boundaries
    try:
        targets = validate_patch(root, patch_text)
        console.print(f"[green][+] Security check passed:[/green] {len(targets)} valid in-workspace target(s)")
        for t in targets:
            console.print(f"  * {t.relative_to(root)}")
    except Exception as exc:
        console.print(f"[bold red]Security or Patch Validation Error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    console.print("\n[bold]Patch Preview:[/bold]")
    console.print(Syntax(patch_text, "diff", theme="monokai", line_numbers=True))

    if not yes:
        confirmed = typer.confirm("Do you explicitly approve applying this patch?")
        if not confirmed:
            console.print("[yellow]Patch application cancelled by user.[/yellow]")
            raise typer.Exit(code=0)

    try:
        apply_patch_to_workspace(root, patch_text)
        console.print("[bold green][+] Patch successfully applied to workspace.[/bold green]")
    except Exception as exc:
        console.print(f"[bold red]Failed to apply patch:[/bold red] {exc}")
        raise typer.Exit(code=1)

@app.command()
def verify(
    path: Path = typer.Argument(
        Path("."),
        help="Path to repository to verify",
        exists=True,
        file_okay=False,
    ),
    profile: str = typer.Option("pytest", "--profile", "-P", help="Test profile (pytest, unittest)"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout in seconds"),
):
    """Run an allowlisted test runner profile and produce an honest verification report."""
    root = path.resolve()
    console.print(f"[bold cyan]Running verification profile '{profile}' on:[/bold cyan] {root}")

    res = run_test_profile(root, profile=profile, timeout_seconds=timeout)

    table = Table(title="Test Verification Evidence")
    table.add_column("Metric", style="bold")
    table.add_column("Result")

    status_color = "green" if res.status == "passed" else "red"
    table.add_row("Exit Status", f"[{status_color}]{res.status.upper()}[/{status_color}]")
    table.add_row("Return Code", str(res.returncode))
    table.add_row("Command Executed", " ".join(res.command))
    console.print(table)

    console.print("\n[bold]Test Process Output:[/bold]")
    console.print(Panel(res.output if res.output else "(No output recorded)", border_style="dim"))

    if res.status != "passed":
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
