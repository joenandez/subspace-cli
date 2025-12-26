"""Agent discovery and loading from multiple sources."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from subspace import debug


@dataclass
class AgentSource:
    """Represents a source for agent definitions."""

    name: str           # e.g., "claude_project", "codex_user", "plugin:feature-dev"
    path: Path
    source_type: str    # "project", "user", "plugin", "override"
    priority: int       # Lower = higher priority


def load_installed_plugins() -> list[dict]:
    """Load installed plugins from ~/.claude/plugins/installed_plugins.json.

    Returns list of dicts with 'name' and 'path' keys for each installed plugin.
    The JSON format is:
    {
      "version": 2,
      "plugins": {
        "plugin-name@scope": [{"installPath": "...", ...}]
      }
    }
    """
    plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not plugins_file.is_file():
        return []

    try:
        data = json.loads(plugins_file.read_text(encoding="utf-8"))
        plugins_dict = data.get("plugins", {})

        result = []
        for plugin_key, installations in plugins_dict.items():
            if not installations:
                continue
            # Take the first installation (most recent)
            install = installations[0]
            install_path = install.get("installPath", "")
            if install_path:
                # Extract plugin name from key (e.g., "feature-dev@scope" -> "feature-dev")
                name = plugin_key.split("@")[0] if "@" in plugin_key else plugin_key
                result.append({"name": name, "path": install_path})

        return result
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        debug(f"Failed to parse plugins file: {plugins_file}: {e}")
        return []


def get_project_root() -> Path:
    """Get the project root (current working directory)."""
    return Path.cwd()


def get_agent_sources(project_root: Path | None = None) -> list[AgentSource]:
    """Return all agent sources in priority order, filtered to existing paths."""
    if project_root is None:
        project_root = get_project_root()

    sources: list[AgentSource] = []

    # Priority 1: Project-level Claude Code agents
    claude_project = project_root / ".claude" / "agents"
    if claude_project.is_dir():
        sources.append(AgentSource("claude_project", claude_project, "project", 1))
        debug(f"Found project claude agents: {claude_project}")

    # Priority 2: Project-level Codex agents
    codex_project = project_root / ".codex" / "agents"
    if codex_project.is_dir():
        sources.append(AgentSource("codex_project", codex_project, "project", 2))
        debug(f"Found project codex agents: {codex_project}")

    # Priority 3: User-level Claude Code agents
    claude_user = Path.home() / ".claude" / "agents"
    if claude_user.is_dir():
        sources.append(AgentSource("claude_user", claude_user, "user", 3))
        debug(f"Found user claude agents: {claude_user}")

    # Priority 4: User-level Codex agents
    codex_user = Path.home() / ".codex" / "agents"
    if codex_user.is_dir():
        sources.append(AgentSource("codex_user", codex_user, "user", 4))
        debug(f"Found user codex agents: {codex_user}")

    # Priority 5: Plugin agents
    for plugin in load_installed_plugins():
        plugin_path_str = plugin.get("path", "")
        if not plugin_path_str:
            continue
        plugin_path = Path(plugin_path_str)
        plugin_agents = plugin_path / "agents"
        if plugin_agents.is_dir():
            plugin_name = plugin.get("name", "unknown")
            sources.append(
                AgentSource(f"plugin:{plugin_name}", plugin_agents, "plugin", 5)
            )
            debug(f"Found plugin agents: {plugin_agents}")

    return sources


def find_agent(name: str, sources: list[AgentSource]) -> tuple[Path, AgentSource] | None:
    """Find agent by name, respecting source priority.

    Returns tuple of (agent_path, source) or None if not found.
    """
    # Strip @ prefix and .md suffix if present
    clean_name = name.lstrip("@")
    if clean_name.endswith(".md"):
        clean_name = clean_name[:-3]

    for source in sorted(sources, key=lambda s: s.priority):
        agent_path = source.path / f"{clean_name}.md"
        if agent_path.is_file():
            debug(f"Found agent '{clean_name}' at {agent_path}")
            return (agent_path, source)

    debug(f"Agent '{clean_name}' not found in any source")
    return None


def list_all_agents(sources: list[AgentSource]) -> list[dict]:
    """List all agents from all sources, first-match wins for duplicates."""
    seen: set[str] = set()
    agents: list[dict] = []

    for source in sorted(sources, key=lambda s: s.priority):
        if not source.path.is_dir():
            continue

        for agent_file in sorted(source.path.glob("*.md")):
            name = agent_file.stem
            if name not in seen:
                seen.add(name)
                frontmatter = parse_frontmatter(agent_file.read_text(encoding="utf-8"))
                agents.append({
                    "name": name,
                    "path": str(agent_file),
                    "source": source.name,
                    "source_type": source.source_type,
                    "description": frontmatter.get("description", ""),
                })

    return agents


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


def load_agent_details(agent_path: Path, source: AgentSource) -> dict:
    """Load full agent details including frontmatter and body."""
    content = agent_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(content)
    body = strip_frontmatter(content)

    return {
        "name": agent_path.stem,
        "path": str(agent_path),
        "source": source.name,
        "source_type": source.source_type,
        "frontmatter": frontmatter,
        "body": body,
    }


def load_agent_instructions(agent_path: Path) -> str:
    """Load agent instructions (body without frontmatter)."""
    content = agent_path.read_text(encoding="utf-8")
    return strip_frontmatter(content)
