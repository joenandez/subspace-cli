# Subspace CLI

Run OpenAI Codex CLI subagents and slash commands programmatically.

## Overview

Subspace provides two powerful capabilities for AI-assisted development:

1. **Subagents** - Run specialized AI agents in isolated Codex sessions
2. **Slash Commands** - Execute predefined prompts/workflows programmatically

This provides:

- **Agent reusability**: Same agent definitions work across Claude Code and Codex
- **Multi-source discovery**: Agents and commands from project, user, and plugin directories
- **Parallel execution**: Run multiple agents concurrently with true parallelism
- **Slash command pipelines**: Chain commands like `/quick_tasks` then `/execute_sync`
- **Namespaced commands**: Organize commands in subdirectories (e.g., `/subspace:sweep`)
- **JSONL streaming**: Real-time event streaming for UI integration
- **Sandbox isolation**: Subagents run in `workspace-write` sandbox mode
- **Context isolation**: Each subagent runs in its own session
- **Security hardening**: Path traversal prevention, input validation

## Installation

```bash
cd subspace-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

After installation, the `subspace` command is available:

```bash
subspace --version
# → subspace 0.1.0
```

### Codex CLI Integration

To enable Codex CLI to recognize `@agent-{name}` syntax and dispatch subagents:

```bash
subspace setup
```

This installs the Subspace integration into `~/.codex/AGENTS.md`. The command is idempotent - running it multiple times is safe.

**Output:**
```
✓ Subspace integration installed to /Users/joe/.codex/AGENTS.md

Codex will now recognize @agent-{name} syntax and can run subagents.

Try these commands:
  subspace subagent list          # See available agents
  subspace subagent show tdd-agent  # Show agent details
```

## Prerequisites

- Python 3.10+
- OpenAI Codex CLI installed and authenticated (`codex` command available)
- Agent markdown files in discovery paths (see Agent Discovery section)

---

## Commands

### Setup Codex integration

```bash
subspace setup
```

Installs Subspace integration into `~/.codex/AGENTS.md` so Codex CLI can:
- Recognize `@agent-{name}` syntax in user input
- Recognize `/{command-name}` syntax for slash commands
- Know how to dispatch subagents via `subspace subagent run/parallel`
- Know how to retrieve and execute slash commands via `subspace command get`
- Understand when to use subagents vs. handling work directly

**Features:**
- Creates `~/.codex/` directory if needed
- Idempotent - safe to run multiple times
- Warns if `codex` CLI is not installed
- Returns exit code 1 if codex is missing (integration still installed)

**Already installed:**
```
✓ Subspace integration already installed in /Users/joe/.codex/AGENTS.md

To reinstall, first remove the '## Subspace Agent Tools' section.
```

---

### Run a single agent

```bash
subspace subagent run [agent] <task>
```

The agent argument is optional. If omitted, runs vanilla Codex without custom instructions.

**With agent (custom instructions):**
```bash
subspace subagent run tdd-agent "write tests for the auth module"
```

**Vanilla mode (no agent):**
```bash
subspace subagent run "explain this codebase"
```

Vanilla mode runs Codex directly without loading any agent definition file. Useful for general-purpose tasks that don't need specialized agent behavior.

**With debug output:**
```bash
subspace subagent run tdd-agent "hello" --debug
```

```
[DEBUG] subspace v0.1.0
[DEBUG] Found user claude agents: /Users/joe/.claude/agents
[DEBUG] Found plugin agents: .../feature-dev/agents
[DEBUG] Found agent 'tdd-agent' at /Users/joe/.claude/agents/tdd-agent.md
[DEBUG] Loading agent: /Users/joe/.claude/agents/tdd-agent.md
[DEBUG] Agent instructions: 5856 chars
[DEBUG] Synced config.toml to .subspace/codex-subagent
[DEBUG] Synced auth.json to .subspace/codex-subagent
[DEBUG] CODEX_HOME: /path/to/.subspace/codex-subagent
[DEBUG] Running tdd-agent (sandbox: workspace-write)
[DEBUG] Command: codex exec --sandbox workspace-write --json
[DEBUG] Payload size: 6612 bytes
<agent response>
```

**Vanilla mode debug output:**
```bash
subspace subagent run "hello" --debug
```

```
[DEBUG] subspace v0.1.0
[DEBUG] Running vanilla Codex (no agent)
[DEBUG] Running vanilla Codex (no agent instructions)
[DEBUG] CODEX_HOME: /path/to/.subspace/codex-subagent
[DEBUG] Running codex (sandbox: workspace-write)
[DEBUG] Command: codex exec --sandbox workspace-write --json
[DEBUG] Payload size: 113 bytes
<response>
```

---

### Run agents in parallel

Run multiple subagents concurrently. Results stream as each agent completes.

```bash
subspace subagent parallel <agent:task> [agent:task ...]
```

**Example:**
```bash
subspace subagent parallel \
  'tdd-agent:Say ONE' \
  'tdd-agent:Say TWO' \
  'tdd-agent:Say THREE'
```

**Output:**
```
============================================================
[tdd-agent] (completed in 2.2s)
============================================================
ONE

============================================================
[tdd-agent] (completed in 14.1s)
============================================================
TWO

============================================================
[tdd-agent] (completed in 14.9s)
============================================================
THREE

[subspace] All complete. Wall time: 14.9s, Total agent time: 31.2s
```

**Agent:task format:**
- Simple: `agent-name:task text here`
- Quoted: `agent-name:"task with spaces"`
- Single quotes: `agent-name:'task with spaces'`

**Parallelism:**
- No built-in limit on concurrent agents
- Recommended: 3-5 agents for general use, 8-10 for heavy workloads
- Practical limits: file descriptors, memory, API rate limits

---

### List available agents

```bash
subspace subagent list
```

**Output:**
```
NAME                 SOURCE                                        TYPE
--------------------------------------------------------------------------------
codebase-analyzer    ...joe/.claude/agents/codebase-analyzer.md    user
codebase-locator     .../joe/.claude/agents/codebase-locator.md    user
tdd-agent            /Users/joe/.claude/agents/tdd-agent.md        user
code-architect       .../feature-dev/agents/code-architect.md      plugin
code-explorer        .../feature-dev/agents/code-explorer.md       plugin
code-reviewer        .../feature-dev/agents/code-reviewer.md       plugin
```

**JSON output:**
```bash
subspace subagent list --output json
```

```json
[
  {
    "name": "tdd-agent",
    "path": "/Users/joe/.claude/agents/tdd-agent.md",
    "source": "claude_user",
    "source_type": "user",
    "description": "Use this agent for strict TDD methodology..."
  }
]
```

---

### Show agent details

```bash
subspace subagent show <agent>
```

**Example:**
```bash
subspace subagent show tdd-agent
```

**Output:**
```
Agent: tdd-agent
Source: claude_user (user)
Path: /Users/joe/.claude/agents/tdd-agent.md

Frontmatter:
  name: tdd-agent
  description: Use this agent for strict TDD methodology...
  color: red

Instructions:
----------------------------------------
## TDD Agent Role

You are a senior engineer optimizing for speed with quality...
```

---

## Slash Commands

Slash commands are predefined prompts stored as markdown files that agents can retrieve and execute programmatically. This enables:

- **Nested workflows**: Meta-prompts that reference other commands
- **Reusable procedures**: Standard operating procedures as executable prompts
- **Dynamic pipelines**: Chain commands like "run /quick_tasks then /execute_sync"
- **Namespaced organization**: Group related commands (e.g., `/subspace:sweep`)

### Get a command prompt

```bash
subspace command get /command-name [args...]
```

This is the primary interface for retrieving executable prompts.

**Basic usage:**
```bash
subspace command get /quick_tasks
```

**Namespaced command:**
```bash
subspace command get /subspace:sweep
```

**With argument interpolation:**
```bash
# If command contains "Deploy $1 to $2 environment"
subspace command get /deploy backend production
# Returns: "Deploy backend to production environment"
```

**JSON output:**
```bash
subspace command get /subspace:sweep --output json
```

```json
{
  "command": "/subspace:sweep",
  "path": "/Users/joe/.claude/commands/subspace/sweep.md",
  "source": "claude_user",
  "args": [],
  "prompt": "## Pre-Commit Cleanup\n\nYou are preparing..."
}
```

---

### List available commands

```bash
subspace command list
```

**Output:**
```
COMMAND                   SOURCE               DESCRIPTION
--------------------------------------------------------------------------------
/bug_hunt                 user
/subspace:analyze_logs    user                 Analyze logs for root cause...
/subspace:clean           user                 Complete cleanup flow - cle...
/subspace:execute_sync    user                 Sequential Build -> Code_Re...
/subspace:quick_tasks     user                 Fast task breakdown from cu...
/subspace:sweep           user                 Light pass clean up flow...
```

**JSON output:**
```bash
subspace command list --output json
```

---

### Show command details

```bash
subspace command show /command-name
```

**Example:**
```bash
subspace command show /subspace:sweep
```

**Output:**
```
Command: /subspace:sweep
Source: claude_user (user)
Path: /Users/joe/.claude/commands/subspace/sweep.md

Frontmatter:
  description: Light pass clean up flow post feature dev/quick fix

Prompt:
----------------------------------------
## Pre-Commit Cleanup

You are preparing recently committed or uncommitted changes...
```

---

### Command Discovery

Commands are discovered from multiple sources in priority order (first match wins):

| Priority | Source | Path | Type |
|----------|--------|------|------|
| 1 | Project Claude | `./.claude/commands/` | project |
| 2 | Project Codex | `./.codex/prompts/` | project |
| 3 | User Claude | `~/.claude/commands/` | user |
| 4 | User Codex | `~/.codex/prompts/` | user |

**Override discovery:**
```bash
subspace command list --commands-dir ~/.claude/commands
```

---

### Namespaced Commands

Commands can be organized in subdirectories. The subdirectory becomes the namespace:

```
~/.claude/commands/
├── deploy.md              → /deploy
└── subspace/
    ├── sweep.md           → /subspace:sweep
    ├── clean.md           → /subspace:clean
    └── quick_tasks.md     → /subspace:quick_tasks
```

**Usage:**
```bash
subspace command get /subspace:sweep
subspace command get /subspace:quick_tasks
```

---

### Argument Interpolation

Commands can accept positional arguments using `$1`, `$2`, etc.:

**Command file (`deploy.md`):**
```markdown
---
description: Deploy a service to an environment
---

Deploy $1 to $2 environment.

1. Build the $1 service
2. Run tests
3. Deploy to $2
```

**Usage:**
```bash
subspace command get /deploy backend staging
# Returns prompt with $1=backend, $2=staging
```

**Special variables:**
- `$1`, `$2`, ... - Positional arguments
- `$@` - All arguments joined by space

---

### Command File Format

```markdown
---
description: Brief description for listing
---

## Command Instructions

Your prompt text here. This is what the agent will execute.

1. First step
2. Second step
3. Final step
```

The frontmatter is optional. The `description` field is shown in `subspace command list`.

---

### Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output` | `text` | Output format: `text` or `json` |
| `--debug` | false | Show detailed execution trace |
| `--commands-dir` | (discovery) | Override: use single directory |

---

## Options

### Run Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output` | `text` | Output format: `text` or `jsonl` |
| `--timeout` | `600` | Timeout in seconds (10 minutes) |
| `--debug` | false | Show detailed execution trace |
| `--agents-dir` | (discovery) | Override: use single directory |

### Parallel Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output` | `text` | Output format: `text` or `jsonl` |
| `--timeout` | `600` | Timeout per agent in seconds |
| `--debug` | false | Show detailed execution trace |
| `--agents-dir` | (discovery) | Override: use single directory |

### List/Show Command Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output` | `text` | Output format: `text` or `json` |
| `--agents-dir` | (discovery) | Override: use single directory |

---

## Agent Discovery

Agents are discovered from multiple sources in priority order (first match wins):

| Priority | Source | Path | Type |
|----------|--------|------|------|
| 1 | Project Claude | `./.claude/agents/` | project |
| 2 | Project Codex | `./.codex/agents/` | project |
| 3 | User Claude | `~/.claude/agents/` | user |
| 4 | User Codex | `~/.codex/agents/` | user |
| 5 | Plugins | `~/.claude/plugins/*/agents/` | plugin |

**Override discovery:**
```bash
subspace subagent list --agents-dir ~/.claude/agents
```

When overridden, all agents show `TYPE: override`.

---

## Output Formats

### Text (default)

Human-readable output with headers and timing info.

### JSONL (for UI streaming)

Real-time JSONL events for programmatic consumption:

**Single agent:**
```bash
subspace subagent run tdd-agent "task" --output jsonl
```

Streams native Codex JSONL events, followed by completion:
```json
{"type": "complete", "agent": "tdd-agent", "elapsed": 8.3, "returncode": 0}
```

**Parallel agents:**
```bash
subspace subagent parallel 'a:task1' 'b:task2' --output jsonl
```

Each event tagged with agent identity:
```json
{"agent_id": "tdd-agent-0", "agent_name": "tdd-agent", "event": {...}}
{"agent_id": "tdd-agent-1", "agent_name": "tdd-agent", "event": {...}}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     subspace CLI                            │
│  subspace subagent {run, parallel, list, show}              │
│  subspace command {get, list, show}                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│core/discovery │ │ core/commands │ │ core/runner   │
│               │ │               │ │               │
│• Agent source │ │• Cmd discovery│ │• Sandbox setup│
│• Priority     │ │• Namespaces   │ │• Cred sync    │
│• Plugin parse │ │• Interpolation│ │• Codex exec   │
│• Frontmatter  │ │• Frontmatter  │ │• JSONL stream │
└───────────────┘ └───────────────┘ │• Async parallel│
                                    └───────┬───────┘
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │   codex exec      │
                                  │ --sandbox         │
                                  │ workspace-write   │
                                  └───────────────────┘
```

### Package Structure

```
subspace-agent/
├── pyproject.toml              # Package metadata, entry point
└── src/subspace/
    ├── __init__.py             # Version (0.1.0), debug()
    ├── __main__.py             # python -m subspace
    ├── cli.py                  # CLI router, subcommand handlers
    └── core/
        ├── commands.py         # Slash command discovery & loading
        ├── discovery.py        # Multi-source agent discovery
        └── runner.py           # Execution, streaming, parallel
```

### Credential & Config Sync

For sandbox mode, credentials and config are synced to workspace:

```
~/.codex/                    .subspace/codex-subagent/
├── config.toml  ────────►   ├── config.toml
├── auth.json    ────────►   ├── auth.json
└── AGENTS.md    ────────►   └── AGENTS.md
```

The `AGENTS.md` sync ensures subagents know how to use slash commands and other Subspace features.

Security: Symlinks are rejected to prevent symlink attacks.

### Payload Structure

```json
{
  "instructions": "<guidance block>\n---\n\n<agent instructions>",
  "task": "<user's task prompt>",
  "metadata": {
    "agentName": "tdd-agent",
    "startedAt": "2025-12-22T18:30:00Z"
  }
}
```

### Guidance Block

Prepended to prevent recursive subagent calls:

```
You ARE the tdd-agent agent executing a task. You are NOT a dispatcher.

CRITICAL CONSTRAINTS:
- Do NOT spawn subagents or call run_subagent.py
- Do NOT delegate to other agents
- Execute the task directly using your own capabilities
- If the task is outside your expertise, say so and stop

Your role: Follow the instructions below and complete the user's task directly.
```

---

## Security Features

### Input Validation

Agent names must match pattern: `^[a-zA-Z0-9_-]+$`

```bash
# These are blocked:
subspace subagent show "../../../etc/passwd"
# Error: Invalid agent name: must contain only alphanumeric, hyphen, or underscore

subspace subagent show "agent with spaces"
# Error: Invalid agent name: must contain only alphanumeric, hyphen, or underscore

subspace subagent show "-dangerous"
# Error: Invalid agent name: cannot start with hyphen
```

### Symlink Protection

Credential sync rejects symlinks to prevent symlink attacks:

```python
if src.is_symlink():
    debug(f"Skipping symlink: {src}")
    return False
```

### Subprocess Isolation

- All agents run in `workspace-write` sandbox mode
- Separate `CODEX_HOME` per workspace
- No shell execution (subprocess with list args)

---

## Parallel Execution Details

### Concurrency Model

Uses Python's `asyncio` with `gather()` for true parallelism:

```python
task_list = [asyncio.create_task(run_agent(...)) for agent in agents]
results = await asyncio.gather(*task_list, return_exceptions=True)
```

### Performance

```
Example: 3 agents with times 2.2s, 14.1s, 14.9s

Wall time:   14.9s  (actual elapsed)
Agent time:  31.2s  (sum of all)
Speedup:     2.1x   (vs sequential)
```

### Error Handling

- Missing agent: Error reported, other agents continue
- Timeout: Agent killed, error in result
- Codex failure: Non-zero return code captured
- Exceptions: Caught via `return_exceptions=True`

---

## Agent File Format

```markdown
---
name: my-agent
description: Brief description for listing/routing
color: blue
---

## Agent Role

You are a specialized agent that...

## Instructions

1. Do this
2. Then that
3. Finally this

## Constraints

- Don't do X
- Always do Y
```

### Frontmatter Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | No | Agent identifier (defaults to filename) |
| `description` | No | Shown in `list`, used for routing |
| `color` | No | Visual indicator (future use) |

---

## Comparison: Claude Code vs Subspace

| Feature | Claude Code | Subspace |
|---------|-------------|----------|
| Agent definitions | `~/.claude/agents/*.md` | Same + discovery |
| Discovery sources | User only | Project, User, Plugins |
| Parallel execution | Native | Native (asyncio) |
| Streaming | Yes | Yes (JSONL) |
| Model | Claude | Codex (GPT) |
| Sandbox | Varies | `workspace-write` |
| Context isolation | Yes | Yes |
| Recursive prevention | Built-in | Guidance block |

---

## Troubleshooting

### "Agent not found"

```bash
# List available agents
subspace subagent list

# Check specific directory
subspace subagent list --agents-dir ~/.claude/agents
```

### "Invalid agent name"

Agent names must be alphanumeric with hyphens/underscores only:
- ✅ `tdd-agent`, `code_reviewer`, `agent123`
- ❌ `../passwd`, `agent name`, `@special`

### "Codex binary not found"

```bash
which codex
codex --version
```

### Timeout errors

```bash
# Increase timeout (default: 600s)
subspace subagent run tdd-agent "complex task" --timeout 1200
```

### Debug execution

```bash
subspace subagent run tdd-agent "task" --debug
```

Shows: version, discovery, agent loading, credential sync, command, payload size.

---

## Files

| File | Purpose |
|------|---------|
| `subspace-agent/` | Installable Python package |
| `subspace-agent/src/subspace/cli.py` | CLI router, handlers, setup command |
| `subspace-agent/src/subspace/core/commands.py` | Slash command discovery & loading |
| `subspace-agent/src/subspace/core/discovery.py` | Multi-source agent discovery |
| `subspace-agent/src/subspace/core/runner.py` | Execution and streaming |
| `~/.claude/agents/*.md` | User agent definitions |
| `~/.claude/commands/*.md` | User slash commands |
| `~/.claude/commands/*/` | Namespaced command directories |
| `~/.codex/prompts/*.md` | User slash commands (Codex) |
| `~/.codex/AGENTS.md` | Codex integration (installed via `subspace setup`) |
| `.subspace/codex-subagent/` | Credential sync (gitignored) |

---

## Future Enhancements

- [ ] `--max-concurrent` flag for parallel execution limits
- [ ] MCP server integration (`subagent.run()` tool)
- [ ] Config file support (`~/.config/subspace/config.toml`)
- [ ] Agent chaining (output of A → input of B)
- [ ] Cost/token tracking per agent
- [ ] PyPI publication
