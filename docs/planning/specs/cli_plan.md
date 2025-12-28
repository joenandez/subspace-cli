# CLI Product Proposal: `subspace`

## Executive Summary

Create a distributable CLI tool (`subspace`) that serves as the foundation for Subspace tooling. The first subcommand group is `subspace subagent` for running Codex subagents using Claude Code agent definitions. Designed for clean interface, easy installation, JSONL streaming for UI integration, and extensibility for future commands.

---

## Proposed Interface

```bash
# Run single agent
subspace subagent run tdd-agent "write tests for auth"

# Run multiple agents in parallel
subspace subagent parallel tdd-agent:"task1" coder:"task2"

# List available agents
subspace subagent list

# Show agent details
subspace subagent show tdd-agent

# With JSONL streaming output (for UI integration)
subspace subagent run tdd-agent "task" --output jsonl

# Version/help
subspace --version
subspace --help
subspace subagent --help
```

**In AGENTS.md:**
```markdown
## Subagents

To delegate work to a specialized agent:
subspace subagent run <agent-name> "<task>"

Available agents: `subspace subagent list`
```

---

## Package Structure

```
subspace-agent/
├── pyproject.toml          # Package config with CLI entry point
├── src/
│   └── subspace/
│       ├── __init__.py         # Version, DEBUG flag, debug() function
│       ├── __main__.py         # python -m subspace
│       ├── cli.py              # CLI router + subcommand handlers
│       └── core/
│           ├── __init__.py
│           ├── discovery.py    # Agent discovery + loading
│           └── runner.py       # Execution + sandbox + streaming
└── scripts/
    └── run_subagent.py         # Original prototype (reference)
```

**Simplifications applied:**
- Consolidated 5 modules → 2 (`discovery.py`, `runner.py`)
- Inline debug logging in `__init__.py` (no separate utils/)
- No separate `commands/` directory (handlers in `cli.py`)
- Start from working prototype, refactor don't rewrite

**Future subcommand groups** (structure supports easy addition):
- `subspace memory` - Memory/context management
- `subspace sync` - Synchronize agents/slash commands across CLI agents

---

## Agent Discovery

### Overview

Agents are discovered from multiple sources with clear precedence. Project-local agents override user-level agents. Easy to extend with new sources.

### Source Hierarchy (checked in order)

| Priority | Source | Path | Description |
|----------|--------|------|-------------|
| 1 | Claude Code (project) | `./.claude/agents/` | Project-specific CC agents |
| 2 | Codex (project) | `./.codex/agents/` | Project-specific Codex agents |
| 3 | Claude Code (user) | `~/.claude/agents/` | User's global CC agents |
| 4 | Codex (user) | `~/.codex/agents/` | User's global Codex agents |
| 5 | Claude Code (plugins) | `{plugin_path}/agents/` | Agents bundled with installed plugins |

### Plugin Agent Discovery

Plugins are discovered from `~/.claude/plugins/installed_plugins.json`:

```json
{
  "plugins": [
    {
      "name": "feature-dev",
      "scope": "@claude-plugins-official",
      "path": "/Users/joe/.claude/plugins/feature-dev"
    }
  ]
}
```

For each plugin, check `{path}/agents/` for agent definitions.

### Resolution Rules

1. **First match wins** - Earlier sources take precedence
2. **Name-based matching** - Agent name = filename without `.md` extension
3. **No deduplication** - If same agent exists in multiple sources, highest priority wins
4. **Explicit override** - `--agents-dir` bypasses discovery, uses single path

### List Output with Sources

```bash
$ subspace subagent list

NAME              SOURCE                                      TYPE
tdd-agent         ./.claude/agents/tdd-agent.md              project (claude)
coder             ~/.claude/agents/coder.md                   user (claude)
feature-explorer  ~/.codex/agents/feature-explorer.md         user (codex)
code-reviewer     ~/.claude/plugins/feature-dev/agents/...    plugin (feature-dev)
```

### Extensibility

Add custom agent paths via config file or environment variables. See [Configuration](#configuration) section.

### Implementation

```python
# subspace/core/discovery.py

@dataclass
class AgentSource:
    name: str           # e.g., "claude_project", "codex_user", "plugin:feature-dev"
    path: Path
    source_type: str    # "project", "user", "plugin"
    priority: int

def get_agent_sources(project_root: Path) -> list[AgentSource]:
    """Return all agent sources in priority order."""
    sources = []

    # Project-level (highest priority)
    sources.append(AgentSource("claude_project", project_root / ".claude/agents", "project", 1))
    sources.append(AgentSource("codex_project", project_root / ".codex/agents", "project", 2))

    # User-level
    sources.append(AgentSource("claude_user", Path("~/.claude/agents").expanduser(), "user", 3))
    sources.append(AgentSource("codex_user", Path("~/.codex/agents").expanduser(), "user", 4))

    # Plugin-level
    for plugin in load_installed_plugins():
        plugin_agents = Path(plugin["path"]) / "agents"
        sources.append(AgentSource(f"plugin:{plugin['name']}", plugin_agents, "plugin", 5))

    # Extra paths from config
    for extra in get_extra_paths():
        sources.append(AgentSource("custom", Path(extra).expanduser(), "custom", 6))

    return [s for s in sources if s.path.exists()]

def find_agent(name: str, sources: list[AgentSource]) -> tuple[Path, AgentSource] | None:
    """Find agent by name, respecting source priority."""
    for source in sorted(sources, key=lambda s: s.priority):
        agent_path = source.path / f"{name}.md"
        if agent_path.exists():
            return (agent_path, source)
    return None

def list_all_agents(sources: list[AgentSource]) -> list[dict]:
    """List all agents from all sources, first-match wins for duplicates."""
    seen = set()
    agents = []
    for source in sorted(sources, key=lambda s: s.priority):
        if not source.path.exists():
            continue
        for agent_file in source.path.glob("*.md"):
            name = agent_file.stem
            if name not in seen:
                seen.add(name)
                agents.append({
                    "name": name,
                    "path": str(agent_file),
                    "source": source.name,
                    "source_type": source.source_type,
                })
    return agents
```

---

## JSONL Streaming Output

### Purpose

Enable UI integration so users can see agents working in real-time (not a black box). Uses Codex's native `--json` flag for structured event streaming.

### Single Agent Output

```bash
subspace subagent run tdd-agent "write tests" --output jsonl
```

Pass-through of Codex's native JSONL events:
```jsonl
{"type": "start", "task": "write tests", ...}
{"type": "message", "content": "Searching for test files...", ...}
{"type": "tool_use", "tool": "Grep", "params": {...}, ...}
{"type": "tool_result", "output": "...", ...}
{"type": "complete", "exit_code": 0, ...}
```

### Parallel Agent Output

```bash
subspace subagent parallel tdd-agent:"task1" coder:"task2" --output jsonl
```

Interleaved events tagged with `agent_id` for UI demuxing:
```jsonl
{"agent_id": "tdd-agent-0", "agent_name": "tdd-agent", "event": {...codex event...}}
{"agent_id": "coder-1", "agent_name": "coder", "event": {...codex event...}}
{"agent_id": "tdd-agent-0", "agent_name": "tdd-agent", "event": {...codex event...}}
```

UI can filter by `agent_id` to render separate panels per agent showing real-time progress.

### Event Types (from Codex --json)

| Event Type | Description |
|------------|-------------|
| `start` | Agent execution started |
| `message` | Assistant message/thinking |
| `tool_use` | Tool invocation (Read, Edit, Bash, etc.) |
| `tool_result` | Tool execution result |
| `error` | Error occurred |
| `complete` | Execution finished |

---

## Debug Mode

### Purpose

Provide visibility into CLI operations for troubleshooting.

### Usage

```bash
subspace subagent run tdd-agent "task" --debug
```

### Debug Output

```
[DEBUG] subspace v0.1.0
[DEBUG] agents_dir: /Users/joe/.claude/agents
[DEBUG] loading agent: tdd-agent.md (2.3kb)
[DEBUG] stripping YAML frontmatter (42 lines)
[DEBUG] syncing credentials to .subspace/codex-subagent/
[DEBUG]   - copied auth.json
[DEBUG]   - copied settings.json
[DEBUG] executing: codex exec --sandbox workspace-write --json -p "..."
[DEBUG] process started, pid: 12345
[DEBUG] streaming events...
[DEBUG] process exited, code: 0, duration: 45.2s
```

### Debug Information Includes

- CLI version
- Agent file location and size
- Frontmatter stripping details
- Credential sync operations
- Full command being executed
- Process lifecycle (pid, exit code, duration)
- Any errors with full context

---

## Installation Options

### Option A: pip (Recommended)

```bash
pip install subspace-agent
# or
pipx install subspace-agent
```

**pyproject.toml:**
```toml
[project]
name = "subspace-agent"
version = "0.1.0"
description = "Subspace CLI - run Codex subagents and more"
requires-python = ">=3.10"
dependencies = []

[project.scripts]
subspace = "subspace.cli:main"
```

### Option B: Homebrew (macOS/Linux)

```bash
brew tap subspace/tools
brew install subspace
```

### Option C: Standalone binary (PyInstaller/Nuitka)

```bash
# Download from GitHub releases
curl -L https://github.com/subspace/subspace-agent/releases/latest/download/subspace-macos -o /usr/local/bin/subspace
chmod +x /usr/local/bin/subspace
```

---

## CLI Framework

**Decision:** Keep **argparse** (no dependencies) with nested subparsers.

| Framework | Pros | Cons |
|-----------|------|------|
| **argparse** (chosen) | No deps, stdlib | Verbose, less pretty |
| Click | Clean API, auto-help | Extra dependency |
| Typer | Type hints, modern | Depends on Click |

---

## CLI Implementation

```python
# subspace/cli.py (simplified - all in one file)

import argparse
from subspace import __version__, debug
from subspace.core.discovery import find_agent, list_all_agents, get_agent_sources
from subspace.core.runner import run_agent, run_parallel

def main():
    parser = argparse.ArgumentParser(prog="subspace", description="Subspace CLI tools")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # subspace subagent ...
    subagent = subparsers.add_parser("subagent", help="Run Codex subagents")
    sub = subagent.add_subparsers(dest="subagent_command", required=True)

    # subspace subagent run <agent> <task>
    run_p = sub.add_parser("run", help="Run a single agent")
    run_p.add_argument("agent", help="Agent name (e.g., tdd-agent)")
    run_p.add_argument("task", help="Task description")
    run_p.add_argument("--output", choices=["text", "jsonl"], default="text",
                       help="Output format (jsonl for UI streaming)")
    run_p.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    run_p.add_argument("--debug", action="store_true", help="Enable debug output")
    run_p.add_argument("--agents-dir", help="Override: use single directory instead of discovery")
    run_p.set_defaults(func=cmd_run)

    # subspace subagent parallel <agent:task>...
    par_p = sub.add_parser("parallel", help="Run multiple agents in parallel")
    par_p.add_argument("pairs", nargs="+", help="agent:task pairs (e.g., tdd-agent:\"write tests\")")
    par_p.add_argument("--output", choices=["text", "jsonl"], default="text")
    par_p.add_argument("--timeout", type=int, default=600)
    par_p.add_argument("--debug", action="store_true")
    par_p.add_argument("--agents-dir", help="Override: use single directory instead of discovery")
    par_p.set_defaults(func=cmd_parallel)

    # subspace subagent list
    list_p = sub.add_parser("list", help="List available agents")
    list_p.add_argument("--output", choices=["text", "json"], default="text")
    list_p.add_argument("--agents-dir", help="Override: use single directory instead of discovery")
    list_p.set_defaults(func=cmd_list)

    # subspace subagent show <agent>
    show_p = sub.add_parser("show", help="Show agent details")
    show_p.add_argument("agent", help="Agent name")
    show_p.add_argument("--output", choices=["text", "json"], default="text")
    show_p.add_argument("--agents-dir", help="Override: use single directory instead of discovery")
    show_p.set_defaults(func=cmd_show)

    # Future: subspace memory ...
    # Future: subspace sync ...

    args = parser.parse_args()
    args.func(args)

def cmd_run(args): ...
def cmd_parallel(args): ...
def cmd_list(args): ...
def cmd_show(args): ...
```

**Simplifications:**
- All CLI code in single `cli.py` (no separate `commands/` module)
- Two output formats only: `text` and `jsonl` (use `jsonl | jq -s` for JSON array)
- Removed `--quiet` flag (unclear semantics with `--output`)

---

## Configuration

> **Note:** Config file support is deferred to Phase 2. For now, use CLI flags.

### Phase 1 (Current): CLI Flags Only

```bash
# Override agent discovery
subspace subagent run --agents-dir ~/.my-agents tdd-agent "task"

# Set timeout
subspace subagent run --timeout 300 tdd-agent "task"

# Enable debug output
subspace subagent run --debug tdd-agent "task"
```

### Phase 2 (Future): Config File Support

Config file: `~/.config/subspace/config.toml`

```toml
[defaults]
timeout = 600
output = "text"

[codex]
bin = "codex"
sandbox = "workspace-write"

[agents]
extra_paths = ["~/my-custom-agents"]
```

Environment variables (Phase 2):
```bash
SUBSPACE_TIMEOUT=600
SUBSPACE_CODEX_BIN=codex
SUBSPACE_AGENTS_EXTRA_PATHS="~/custom:~/more-agents"
```

---

## AGENTS.md Integration Example

```markdown
## Available Tools

### Subagents

Delegate specialized work to focused agents:

| Agent | Purpose |
|-------|---------|
| `tdd-agent` | Write tests using TDD methodology |
| `coder` | Implement features with clean code |
| `reviewer` | Review code for issues |

**Usage:**
\`\`\`bash
# Single agent
subspace subagent run tdd-agent "write tests for UserService"

# Multiple agents in parallel
subspace subagent parallel tdd-agent:"write tests" coder:"implement feature"

# List all agents
subspace subagent list

# Stream output for monitoring
subspace subagent run tdd-agent "task" --output jsonl
\`\`\`
```

---

## Implementation Plan

### Phase 1 (MVP)

| Step | Work | Complexity |
|------|------|------------|
| 1 | Refactor prototype into `src/subspace/` package | Low |
| 2 | Add `pyproject.toml` with entry point | Low |
| 3 | Implement CLI router with nested subparsers | Medium |
| 4 | Implement multi-source agent discovery (CC, Codex, plugins) | Medium |
| 5 | Implement `subspace subagent run` with JSONL streaming | Medium |
| 6 | Implement `subspace subagent parallel` with tagged events | Medium |
| 7 | Implement `subspace subagent list/show` with source display | Low |
| 8 | Add inline `--debug` mode | Low |
| 9 | Manual validation of `pip install -e .` | Low |

### Phase 2 (Future)

| Step | Work | Complexity |
|------|------|------------|
| 10 | Add config file support | Low |
| 11 | Publish to PyPI as `subspace-agent` | Low |
| 12 | Create Homebrew formula | Medium |
| 13 | Build standalone binaries | Medium |

**Simplifications applied:**
- Start from working prototype (step 1)
- Config file deferred to Phase 2 (step 10)
- Inline debug logging (no separate module)

---

## Distribution Strategy

### Phase 1: Local install (Now)
```bash
cd subspace-agent
pip install -e .
```

### Phase 2: PyPI (Public release)
```bash
pip install subspace-agent
```

### Phase 3: Homebrew tap
```bash
brew install subspace/tools/subspace
```

### Phase 4: Standalone binaries
GitHub releases with pre-built binaries for macOS/Linux/Windows.

---

## Current State

The prototype `scripts/run_subagent.py` already implements:
- Single agent execution with sandbox mode
- Parallel execution via asyncio
- Credential sync to `.subspace/codex-subagent/`
- `--list` and `--show` commands
- JSON output format
- Timeout handling
- Debug and quiet modes

**Next step:** Restructure as installable `subspace-agent` package with proper CLI structure and JSONL streaming.
