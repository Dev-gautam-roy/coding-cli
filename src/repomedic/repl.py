"""Interactive REPL shell for RepoMedic CLI."""

import sys
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
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
from .patch_applier import apply_patch_to_workspace
from .patch_validator import validate_patch
from .test_runner import run_test_profile

console = Console()

COMMANDS = [
    "help",
    "doctor",
    "inspect",
    "diagnose",
    "diff",
    "apply",
    "verify",
    "fix",
    "workspace",
    "clear",
    "exit",
    "quit",
]

completer = WordCompleter(COMMANDS, ignore_case=True)

class RepoMedicSession:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.last_diagnosis: Diagnosis | None = None
        self.last_patch: str | None = None

    def print_banner(self):
        banner = """[bold cyan]
  ____                       __  __          _ _      
 |  _ \ ___ _ __   ___      |  \/  | ___  __| (_) ___ 
 | |_) / _ \ '_ \ / _ \_____| |\/| |/ _ \/ _` | |/ __|
 |  _ <  __/ |_) | (_) |____| |  | |  __/ (_| | | (__ 
 |_| \_\___| .__/ \___/     |_|  |_|\___|\__,_|_|\___|
           |_|                                         
[/bold cyan]
[bold green]Interactive Terminal Coding Agent for Repository Diagnosis & Repair[/bold green]
[dim]Type [bold cyan]help[/bold cyan] for commands, [bold cyan]fix[/bold cyan] for 1-click autonomous repair loop, or [bold cyan]exit[/bold cyan] to quit.[/dim]
"""
        console.print(Panel(banner, border_style="cyan"))
        console.print(f"[bold]Active Workspace:[/bold] [yellow]{self.workspace}[/yellow]\n")

    def cmd_help(self):
        table = Table(title="RepoMedic Interactive Commands", border_style="cyan")
        table.add_column("Command", style="bold green")
        table.add_column("Description")
        table.add_row("inspect [path]", "Inspect repository manifests, project type & candidate files")
        table.add_row("doctor", "Check environment, Python version, git & AI provider")
        table.add_row("diagnose [log_file]", "Run Nemotron/LLM diagnosis & propose patch")
        table.add_row("diff", "Preview the last proposed code patch")
        table.add_row("apply", "Validate security boundary and apply proposed patch")
        table.add_row("verify [pytest|unittest]", "Run test suite and verify genuine test pass/fail")
        table.add_row("fix", "[bold yellow]Auto-Repair Loop[/bold yellow]: Diagnose -> Preview -> Approve -> Verify")
        table.add_row("workspace <path>", "Change current target repository workspace")
        table.add_row("clear", "Clear terminal screen")
        table.add_row("exit / quit", "Exit interactive shell")
        console.print(table)

    def cmd_doctor(self):
        from .cli import doctor
        doctor()

    def cmd_inspect(self, target_path: str = ""):
        path = Path(target_path) if target_path else self.workspace
        if not path.is_dir():
            console.print(f"[bold red]Error: Directory '{path}' does not exist.[/bold red]")
            return
        result = discover_repository(path)
        console.print(Panel(f"Target: [bold]{result.root}[/bold]\nType: [bold cyan]{result.project_type.upper()}[/bold cyan]\nManifests: {', '.join(result.manifests) if result.manifests else 'None'}\nCandidate files: {len(result.source_files)}", title="Repository Inspection"))
        for f in result.source_files[:10]:
            console.print(f"  * {f}")
        if len(result.source_files) > 10:
            console.print(f"  ... and {len(result.source_files)-10} more")

    def cmd_diagnose(self, log_arg: str = ""):
        log_path = Path(log_arg) if log_arg else None
        console.print(f"[bold cyan]Scanning repository context...[/bold cyan]")
        context = collect_repository_context(self.workspace, log_path=log_path)
        console.print(f"  [+] Included files: {len(context.report.included_files)} ({context.report.total_tokens_approx} tokens)")

        try:
            settings = load_settings()
        except Exception as exc:
            console.print(f"[bold red]Configuration error:[/bold red] {exc}")
            return

        console.print(f"[bold green]Calling {settings.provider} ({settings.model})...[/bold green]")
        prompt = build_diagnosis_prompt(context)
        try:
            raw = ask_model(settings, SYSTEM_PROMPT, prompt)
            diag = parse_and_validate_diagnosis(raw)
            self.last_diagnosis = diag
            self.last_patch = diag.patch
        except Exception as exc:
            console.print(f"[bold red]Diagnosis failed:[/bold red] {exc}")
            return

        console.print(Panel(diag.summary, title="[bold green]Diagnosis Result[/bold green]", border_style="green"))
        console.print(f"[bold]Root Cause:[/bold] {diag.likely_root_cause}")
        console.print(f"[bold]Target Files:[/bold] {', '.join(diag.proposed_files)}")
        console.print("\n[bold]Proposed Patch:[/bold]")
        console.print(Syntax(diag.patch, "diff", theme="monokai", line_numbers=True))

    def cmd_diff(self):
        if not self.last_patch:
            console.print("[yellow]No patch proposed yet. Run 'diagnose' or 'fix' first.[/yellow]")
            return
        console.print(Panel("[bold]Current Proposed Patch[/bold]", border_style="cyan"))
        console.print(Syntax(self.last_patch, "diff", theme="monokai", line_numbers=True))

    def cmd_apply(self):
        if not self.last_patch:
            console.print("[yellow]No patch to apply. Run 'diagnose' first.[/yellow]")
            return
        try:
            targets = validate_patch(self.workspace, self.last_patch)
            console.print(f"[green][+] Security check passed:[/green] {len(targets)} valid in-workspace target(s)")
            for t in targets:
                console.print(f"  * {t.relative_to(self.workspace)}")
        except Exception as exc:
            console.print(f"[bold red]Security validation failed:[/bold red] {exc}")
            return

        console.print(Syntax(self.last_patch, "diff", theme="monokai", line_numbers=True))
        confirm = console.input("[bold yellow]Apply this patch to the workspace? [y/N]: [/bold yellow]").strip().lower()
        if confirm != "y":
            console.print("[dim]Aborted by user.[/dim]")
            return

        try:
            apply_patch_to_workspace(self.workspace, self.last_patch)
            console.print("[bold green][+] Patch successfully applied![/bold green]")
        except Exception as exc:
            console.print(f"[bold red]Failed to apply patch:[/bold red] {exc}")

    def cmd_verify(self, profile: str = "pytest"):
        prof = profile if profile in ("pytest", "unittest") else "pytest"
        console.print(f"[bold cyan]Running verification ({prof}) on:[/bold cyan] {self.workspace}")
        res = run_test_profile(self.workspace, profile=prof)
        status_color = "green" if res.status == "passed" else "red"
        console.print(f"Status: [{status_color} bold]{res.status.upper()}[/{status_color} bold] (Exit Code: {res.returncode})")
        console.print(Panel(res.output[-2000:] if res.output else "(No output)", border_style="dim"))

    def cmd_fix(self):
        """Full end-to-end interactive self-repair workflow."""
        console.print(Panel.fit("[bold magenta]Starting RepoMedic Autonomous Repair Loop[/bold magenta]"))
        
        # 1. Baseline test
        console.print("\n[bold]Step 1: Running baseline test to capture failure evidence...[/bold]")
        base_res = run_test_profile(self.workspace, profile="pytest")
        if base_res.status == "passed":
            console.print("[bold green][+] Tests are already passing! No repair needed.[/bold green]")
            return
        console.print(f"[red]Tests failed as expected (Exit code: {base_res.returncode})[/red]")

        # 2. Diagnose with AI
        console.print("\n[bold]Step 2: Diagnosing root cause with AI model...[/bold]")
        context = collect_repository_context(self.workspace)
        context.error_log = base_res.output
        context.report.log_included = True

        try:
            settings = load_settings()
        except Exception as exc:
            console.print(f"[bold red]Configuration error:[/bold red] {exc}")
            return

        console.print(f"[green]Calling {settings.provider} ({settings.model})...[/green]")
        prompt = build_diagnosis_prompt(context)
        try:
            raw = ask_model(settings, SYSTEM_PROMPT, prompt)
            diag = parse_and_validate_diagnosis(raw)
            self.last_diagnosis = diag
            self.last_patch = diag.patch
        except Exception as exc:
            console.print(f"[bold red]Diagnosis failed:[/bold red] {exc}")
            return

        console.print(Panel(f"[bold]Summary:[/bold] {diag.summary}\n[bold]Root Cause:[/bold] {diag.likely_root_cause}", title="Root Cause Analysis", border_style="cyan"))

        # 3. Security Check & Human Approval Gate
        console.print("\n[bold]Step 3: Security boundary validation & diff preview...[/bold]")
        try:
            targets = validate_patch(self.workspace, diag.patch)
            console.print(f"[green][+] Security check passed:[/green] {len(targets)} valid target(s)")
        except Exception as exc:
            console.print(f"[bold red]Security boundary check rejected patch:[/bold red] {exc}")
            return

        console.print(Syntax(diag.patch, "diff", theme="monokai", line_numbers=True))
        confirm = console.input("\n[bold yellow]Do you approve applying this patch? [y/N]: [/bold yellow]").strip().lower()
        if confirm != "y":
            console.print("[dim]Repair cancelled by user.[/dim]")
            return

        # 4. Apply
        console.print("\n[bold]Step 4: Applying approved patch...[/bold]")
        apply_patch_to_workspace(self.workspace, diag.patch)
        console.print("[green][+] Patch applied.[/green]")

        # 5. Verify
        console.print("\n[bold]Step 5: Executing test runner for verified evidence...[/bold]")
        post_res = run_test_profile(self.workspace, profile="pytest")
        if post_res.status == "passed":
            console.print(Panel.fit("[bold green][SUCCESS] Repair verified! Tests passed with exit code 0.[/bold green]", border_style="green"))
        else:
            console.print(Panel.fit(f"[bold red][FAILED] Tests still failing (Exit code {post_res.returncode}).[/bold red]", border_style="red"))

def run_interactive_shell(initial_path: Path | None = None):
    workspace = (initial_path or Path(".")).resolve()
    session_state = RepoMedicSession(workspace)
    session_state.print_banner()

    history = InMemoryHistory()
    session = PromptSession(history=history, completer=completer)

    while True:
        try:
            prompt_text = f"repomedic [{session_state.workspace.name}]> "
            user_input = session.prompt(prompt_text).strip()
            if not user_input:
                continue

            parts = user_input.split()
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in ("exit", "quit", "q"):
                console.print("[dim]Exiting RepoMedic. Goodbye![/dim]")
                break
            elif cmd == "clear":
                console.clear()
            elif cmd == "help":
                session_state.cmd_help()
            elif cmd == "doctor":
                session_state.cmd_doctor()
            elif cmd == "inspect":
                session_state.cmd_inspect(args[0] if args else "")
            elif cmd == "diagnose":
                session_state.cmd_diagnose(args[0] if args else "")
            elif cmd == "diff":
                session_state.cmd_diff()
            elif cmd == "apply":
                session_state.cmd_apply()
            elif cmd == "verify":
                session_state.cmd_verify(args[0] if args else "pytest")
            elif cmd == "fix":
                session_state.cmd_fix()
            elif cmd == "workspace":
                if args:
                    new_path = Path(args[0]).resolve()
                    if new_path.is_dir():
                        session_state.workspace = new_path
                        console.print(f"[green]Workspace set to:[/green] {new_path}")
                    else:
                        console.print(f"[bold red]Error: '{new_path}' is not a directory.[/bold red]")
                else:
                    console.print(f"[bold]Active Workspace:[/bold] {session_state.workspace}")
            else:
                console.print(f"[yellow]Unknown command '{cmd}'. Type [bold cyan]help[/bold cyan] for commands.[/yellow]")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Interrupted. Type 'exit' to quit.[/dim]")
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
