"""Slash command discovery and loading from multiple sources.

Commands are markdown files in .claude/commands/ or .codex/commands/ directories.
They can contain prompts that agents execute programmatically.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from subspace import debug


@dataclass
class CommandSource:
    """Represents a source for slash command definitions."""

    name: str           # e.g., "claude_project", "codex_user"
    path: Path
    source_type: str    # "project", "user", "override"
    priority: int       # Lower = higher priority


# Valid command name pattern: alphanumeric, hyphen, underscore only
# Commands can optionally start with /
COMMAND_NAME_PATTERN = re.compile(r"^/?[a-zA-Z0-9_-]+$")


def validate_command_name(name: str) -> str:
    """Validate and normalize command name.

    Strips leading / if present. Raises ValueError if name contains unsafe characters.
    Returns the normalized name (without leading /).
    """
    if not name:
        raise ValueError("Command name cannot be empty")

    # Normalize: strip leading /
    clean_name = name.lstrip("/")

    if not clean_name:
        raise ValueError("Command name cannot be just '/'")

    if not COMMAND_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid command name '{name}': must contain only alphanumeric, "
            "hyphen, or underscore characters (optional leading /)"
        )

    if clean_name.startswith("-"):
        raise ValueError(f"Invalid command name '{name}': cannot start with hyphen")

    return clean_name


def get_project_root() -> Path:
    """Get the project root (current working directory)."""
    return Path.cwd()


def get_command_sources(project_root: Path | None = None) -> list[CommandSource]:
    """Return all command sources in priority order, filtered to existing paths."""
    if project_root is None:
        project_root = get_project_root()

    sources: list[CommandSource] = []

    # Priority 1: Project-level Claude Code commands
    claude_project = project_root / ".claude" / "commands"
    if claude_project.is_dir():
        sources.append(CommandSource("claude_project", claude_project, "project", 1))
        debug(f"Found project claude commands: {claude_project}")

    # Priority 2: Project-level Codex commands
    codex_project = project_root / ".codex" / "commands"
    if codex_project.is_dir():
        sources.append(CommandSource("codex_project", codex_project, "project", 2))
        debug(f"Found project codex commands: {codex_project}")

    # Priority 3: User-level Claude Code commands
    claude_user = Path.home() / ".claude" / "commands"
    if claude_user.is_dir():
        sources.append(CommandSource("claude_user", claude_user, "user", 3))
        debug(f"Found user claude commands: {claude_user}")

    # Priority 4: User-level Codex commands
    codex_user = Path.home() / ".codex" / "commands"
    if codex_user.is_dir():
        sources.append(CommandSource("codex_user", codex_user, "user", 4))
        debug(f"Found user codex commands: {codex_user}")

    return sources


def find_command(name: str, sources: list[CommandSource]) -> tuple[Path, CommandSource] | None:
    """Find command by name, respecting source priority.

    Args:
        name: Command name (with or without leading /)
        sources: List of command sources to search

    Returns:
        Tuple of (command_path, source) or None if not found.
    """
    # Validate and normalize name
    try:
        clean_name = validate_command_name(name)
    except ValueError:
        return None

    # Also strip .md suffix if present
    if clean_name.endswith(".md"):
        clean_name = clean_name[:-3]

    for source in sorted(sources, key=lambda s: s.priority):
        command_path = source.path / f"{clean_name}.md"
        if command_path.is_file():
            debug(f"Found command '/{clean_name}' at {command_path}")
            return (command_path, source)

    debug(f"Command '/{clean_name}' not found in any source")
    return None


def list_all_commands(sources: list[CommandSource]) -> list[dict]:
    """List all commands from all sources, first-match wins for duplicates."""
    seen: set[str] = set()
    commands: list[dict] = []

    for source in sorted(sources, key=lambda s: s.priority):
        if not source.path.is_dir():
            continue

        for command_file in sorted(source.path.glob("*.md")):
            name = command_file.stem
            if name not in seen:
                seen.add(name)
                frontmatter = parse_frontmatter(command_file.read_text(encoding="utf-8"))
                commands.append({
                    "name": f"/{name}",
                    "path": str(command_file),
                    "source": source.name,
                    "source_type": source.source_type,
                    "description": frontmatter.get("description", ""),
                })

    return commands


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, flags=re.DOTALL)
    if not match:
        return {}

    frontmatter: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    return frontmatter


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    pattern = r"^---\s*\n.*?\n---\s*\n"
    return re.sub(pattern, "", content, count=1, flags=re.DOTALL)


def load_command_details(command_path: Path, source: CommandSource) -> dict:
    """Load full command details including frontmatter and body."""
    content = command_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(content)
    body = strip_frontmatter(content)

    return {
        "name": f"/{command_path.stem}",
        "path": str(command_path),
        "source": source.name,
        "source_type": source.source_type,
        "frontmatter": frontmatter,
        "body": body,
    }


def load_command_prompt(command_path: Path) -> str:
    """Load command prompt text (body without frontmatter).

    This is the main function used by agents to get the executable prompt.
    """
    content = command_path.read_text(encoding="utf-8")
    return strip_frontmatter(content).strip()


def interpolate_arguments(prompt: str, args: list[str]) -> str:
    """Interpolate positional arguments into the prompt.

    Replaces $1, $2, etc. with corresponding arguments.
    Also supports $@ for all arguments joined by space.

    Args:
        prompt: The raw prompt text with placeholders
        args: List of positional arguments

    Returns:
        Prompt with arguments interpolated
    """
    result = prompt

    # Replace $@ with all arguments
    if "$@" in result:
        result = result.replace("$@", " ".join(args))

    # Replace positional arguments $1, $2, etc.
    for i, arg in enumerate(args, start=1):
        result = result.replace(f"${i}", arg)

    return result
