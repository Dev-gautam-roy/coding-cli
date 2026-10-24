"""Repository inspection and project structure discovery."""

from dataclasses import dataclass, field
from pathlib import Path
from .security import is_path_excluded

SUPPORTED_MANIFESTS = [
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "poetry.lock",
    "pytest.ini",
    "package.json",
    "Cargo.toml",
    "go.mod",
]

@dataclass
class DiscoveryResult:
    root: Path
    manifests: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    project_type: str = "unknown"

def discover_repository(workspace: Path) -> DiscoveryResult:
    """Inspect repository root, locate manifests, and list candidate source files."""
    root = workspace.resolve(strict=True)

    manifests = [m for m in SUPPORTED_MANIFESTS if (root / m).is_file()]

    # Infer project type
    project_type = "unknown"
    if any(m in manifests for m in ["pyproject.toml", "requirements.txt", "setup.py", "pytest.ini"]):
        project_type = "python"
    elif "package.json" in manifests:
        project_type = "javascript/node"
    elif "Cargo.toml" in manifests:
        project_type = "rust"
    elif "go.mod" in manifests:
        project_type = "go"

    # Enumerate candidate source files
    source_files: list[str] = []
    for item in root.rglob("*"):
        if item.is_file():
            try:
                rel = item.relative_to(root)
            except ValueError:
                continue

            if is_path_excluded(rel):
                continue

            # Only include text source/test files
            if rel.suffix.lower() in {".py", ".toml", ".ini", ".cfg", ".json", ".md", ".txt", ".yaml", ".yml"}:
                source_files.append(str(rel).replace("\\", "/"))

    return DiscoveryResult(
        root=root,
        manifests=manifests,
        source_files=sorted(source_files),
        project_type=project_type,
    )
