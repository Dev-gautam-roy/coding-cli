"""Claude Code style interactive terminal coding agent with tools and agentic loop."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table

from .config import Settings, load_settings
from .patch_applier import apply_patch_to_workspace
from .patch_validator import validate_patch
from .security import is_path_excluded, validate_workspace_path
from .test_runner import run_test_profile

console = Console()

# Tools definitions for the Agentic Loop
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "Read the contents of a specific file in the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file from workspace root"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory within the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path (default: current dir, '')"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_code",
            "description": "Search for a regex or string across repository source files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or regex"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_patch",
            "description": "Propose a unified diff patch to modify, repair, or create files in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string", "description": "Reason for the patch"},
                    "patch": {"type": "string", "description": "Standard unified diff starting with --- and +++"}
                },
                "required": ["explanation", "patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Execute the workspace test suite (pytest or unittest) and return exit code + output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {
                        "type": "string",
                        "enum": ["pytest", "unittest"],
                        "description": "Test profile to run (default: pytest)"
                    }
                },
            },
        },
    },
]

CLAUDE_STYLE_SYSTEM_PROMPT = """You are RepoMedic, an elite interactive terminal coding agent (built like Claude Code).
You operate directly on the user's software repository to diagnose, investigate, write code, repair bugs, and run tests.

You have access to tools:
- `view_file(path)`: inspect file content
- `list_files(path)`: list directory entries
- `grep_code(query)`: search codebase
- `propose_patch(explanation, patch)`: propose a unified diff patch for approval
- `run_tests(profile)`: run the test suite and verify changes

CRITICAL OPERATIONAL RULES:
1. Always investigate relevant files and test failures first using `view_file`, `list_files`, or `grep_code`.
2. When fixing a bug or editing code, ALWAYS use `propose_patch` with a clean, syntactically valid unified diff.
3. Be concise and proactive like Claude Code. Explain what you found in short sentences.
4. Never assume tests passed without running `run_tests`.
"""

class ClaudeCodeAgent:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.history: list[dict[str, Any]] = [
            {"role": "system", "content": CLAUDE_STYLE_SYSTEM_PROMPT}
        ]
        self.settings: Settings | None = None
        self._load_config()

    def _load_config(self):
        try:
            self.settings = load_settings()
        except Exception:
            self.settings = None

    def execute_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """Execute tool with strict safety controls."""
        if tool_name == "view_file":
            rel_path = args.get("path", "")
            try:
                target = validate_workspace_path(self.workspace, rel_path)
                if not target.is_file():
                    return f"Error: File '{rel_path}' not found."
                content = target.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                # Limit to 300 lines for prompt budget
                truncated = "\n".join(lines[:300])
                if len(lines) > 300:
                    truncated += f"\n... [truncated {len(lines) - 300} lines]"
                return truncated
            except Exception as e:
                return f"Error reading file: {e}"

        elif tool_name == "list_files":
            rel_path = args.get("path", "")
            try:
                target = validate_workspace_path(self.workspace, rel_path) if rel_path else self.workspace
                if not target.is_dir():
                    return f"Error: '{rel_path}' is not a directory."
                entries = []
                for item in sorted(target.iterdir()):
                    if is_path_excluded(item.name):
                        continue
                    suffix = "/" if item.is_dir() else ""
                    entries.append(f"{item.name}{suffix}")
                return "\n".join(entries[:50]) or "(Empty directory)"
            except Exception as e:
                return f"Error listing files: {e}"

        elif tool_name == "grep_code":
            query = args.get("query", "")
            matches = []
            try:
                regex = re.compile(query, re.IGNORECASE)
                for item in self.workspace.rglob("*"):
                    if item.is_file() and not is_path_excluded(item.relative_to(self.workspace)):
                        if item.suffix.lower() in {".py", ".toml", ".json", ".js", ".ts", ".txt", ".md"}:
                            try:
                                for line_idx, line in enumerate(item.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                                    if regex.search(line):
                                        rel = item.relative_to(self.workspace)
                                        matches.append(f"{rel}:{line_idx}: {line.strip()}")
                                        if len(matches) >= 25:
                                            break
                            except Exception:
                                continue
                    if len(matches) >= 25:
                        break
                return "\n".join(matches) if matches else "No matches found."
            except Exception as e:
                return f"Grep error: {e}"

        elif tool_name == "propose_patch":
            patch = args.get("patch", "")
            explanation = args.get("explanation", "")
            console.print(Panel(f"[bold cyan]Proposed Patch:[/bold cyan] {explanation}", border_style="cyan"))
            console.print(Syntax(patch, "diff", theme="monokai", line_numbers=True))

            # Security validation
            try:
                targets = validate_patch(self.workspace, patch)
                console.print(f"[green]✓ Security check passed:[/green] {len(targets)} target(s) inside workspace")
            except Exception as e:
                return f"Patch rejected by safety validator: {e}"

            # Human Approval Gate (Claude Code style)
            confirm = console.input("\n[bold yellow]Apply this change? [y/N/e(dit)]: [/bold yellow]").strip().lower()
            if confirm == "y":
                try:
                    apply_patch_to_workspace(self.workspace, patch)
                    console.print("[bold green]✓ Patch applied successfully![/bold green]\n")
                    return "Patch was approved and applied by user."
                except Exception as e:
                    return f"Failed to apply patch: {e}"
            else:
                console.print("[yellow]Patch declined by user.[/yellow]\n")
                return "User rejected the proposed patch."

        elif tool_name == "run_tests":
            profile = args.get("profile", "pytest")
            console.print(f"[dim]⚡ Running {profile} in workspace...[/dim]")
            res = run_test_profile(self.workspace, profile=profile)
            color = "green" if res.status == "passed" else "red"
            console.print(f"[{color}]Tests {res.status.upper()} (Exit code: {res.returncode})[/{color}]")
            output_snippet = res.output[-1500:] if res.output else "(No output)"
            return f"Status: {res.status}\nExit code: {res.returncode}\nOutput:\n{output_snippet}"

        return f"Unknown tool: {tool_name}"

    def step(self, user_message: str):
        """Single user turn driving an agentic step or tool call."""
        if not self.settings:
            try:
                self.settings = load_settings()
            except Exception as exc:
                console.print(Panel(f"[bold red]AI Provider Not Configured[/bold red]\n{exc}\n\n[dim]Run /doctor or create a .env file with your API key.[/dim]", border_style="red"))
                return

        self.history.append({"role": "user", "content": user_message})

        from openai import OpenAI
        client = OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
            timeout=60.0,
        )

        max_turns = 6
        turn = 0

        while turn < max_turns:
            turn += 1
            with console.status(f"[cyan]RepoMedic thinking ({self.settings.provider} - {self.settings.model})...[/cyan]", spinner="dots"):
                try:
                    response = client.chat.completions.create(
                        model=self.settings.model,
                        messages=self.history,
                        tools=TOOLS_SCHEMA,
                        tool_choice="auto",
                        temperature=0.2,
                    )
                except Exception as exc:
                    # Fallback if model doesn't support tools schema
                    console.print(f"[dim]Tools schema not supported by model, falling back to direct prompt mode: {exc}[/dim]")
                    try:
                        fallback_resp = client.chat.completions.create(
                            model=self.settings.model,
                            messages=self.history,
                            temperature=0.2,
                        )
                        content = fallback_resp.choices[0].message.content or ""
                        console.print(Markdown(content))
                        self.history.append({"role": "assistant", "content": content})
                        return
                    except Exception as fallback_exc:
                        console.print(f"[bold red]API Error:[/bold red] {fallback_exc}")
                        return

            msg = response.choices[0].message
            tool_calls = msg.tool_calls

            if msg.content:
                console.print(Markdown(msg.content))

            # Store assistant response in history
            msg_dict = {"role": "assistant", "content": msg.content or ""}
            if tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ]
            self.history.append(msg_dict)

            if not tool_calls:
                break

            # Execute tool calls
            for tc in tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                console.print(f"[bold blue]❯ Tool Call:[/bold blue] [cyan]{func_name}[/cyan]({', '.join(f'{k}={v}' for k, v in args.items())})")
                tool_result = self.execute_tool(func_name, args)

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })


def run_claude_cli(workspace_path: Path | None = None):
    """Launch full-fledged Claude Code style interactive shell."""
    workspace = (workspace_path or Path(".")).resolve()
    agent = ClaudeCodeAgent(workspace)

    # Print Claude Code aesthetic header
    console.print()
    console.print("[bold cyan]RepoMedic[/bold cyan] [dim]v0.1.0[/dim] [bold green](Claude Code Mode)[/bold green]")
    provider_info = f"{agent.settings.provider} ({agent.settings.model})" if agent.settings else "[red]No API key configured[/red]"
    console.print(f"[dim]cwd: {workspace} | model: {provider_info}[/dim]")
    console.print("[dim]Type your request naturally, or type [bold cyan]/help[/bold cyan], [bold cyan]/doctor[/bold cyan], [bold cyan]/exit[/bold cyan].[/dim]\n")

    history = InMemoryHistory()
    session = PromptSession(history=history)

    prompt_style = Style.from_dict({
        "prompt": "ansicyan bold",
    })

    while True:
        try:
            user_input = session.prompt(
                HTML("<prompt>repomedic &gt; </prompt>"),
                style=prompt_style,
            ).strip()

            if not user_input:
                continue

            # Handle slash commands
            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("[dim]Goodbye![/dim]")
                break
            elif user_input.lower() == "/clear":
                console.clear()
                continue
            elif user_input.lower() == "/doctor":
                from .cli import doctor
                doctor()
                continue
            elif user_input.lower() == "/help":
                table = Table(title="RepoMedic Slash Commands", border_style="cyan")
                table.add_column("Command", style="bold green")
                table.add_column("Description")
                table.add_row("/doctor", "Check environment and API provider status")
                table.add_row("/clear", "Clear terminal screen")
                table.add_row("/exit", "Exit the CLI session")
                table.add_row("<anything else>", "Natural language instruction for the coding agent (e.g. 'find the bug and fix it')")
                console.print(table)
                continue

            # Run agent loop
            agent.step(user_input)
            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Interrupted. Type /exit to quit.[/dim]")
        except Exception as exc:
            console.print(f"[bold red]Unexpected error:[/bold red] {exc}")
