# subspace-agent

Subspace CLI - run Codex subagents and more.

## Installation

```bash
pip install subspace-agent
```

Or install from source:

```bash
cd subspace-agent
pip install -e .
```

## Setup

After installation, run setup to enable Codex CLI integration:

```bash
subspace setup
```

This installs the Subspace integration into `~/.codex/AGENTS.md` so Codex can recognize `@agent-{name}` syntax.

## Requirements

- Python 3.10+
- OpenAI Codex CLI installed (`codex` command) - for run/parallel commands

## Usage

### Run a single agent

```bash
subspace subagent run [agent] <task>
```

**With agent:**
```bash
subspace subagent run tdd-agent "write tests for the auth module"
```

**Vanilla mode (no agent):**
```bash
subspace subagent run "explain this codebase"
```

### Run multiple agents in parallel

```bash
subspace subagent parallel tdd-agent:"write tests" coder:"implement feature"
```

### List available agents

```bash
subspace subagent list
```

### Show agent details

```bash
subspace subagent show tdd-agent
```

### JSONL streaming output

```bash
subspace subagent run tdd-agent "task" --output jsonl
```

## Agent Discovery

Agents are discovered from multiple sources in priority order:

1. Project-level `./.claude/agents/`
2. Project-level `./.codex/agents/`
3. User-level `~/.claude/agents/`
4. User-level `~/.codex/agents/`
5. Plugin agents from installed Claude Code plugins

Override with `--agents-dir`:

```bash
subspace subagent list --agents-dir ~/my-agents
```

## License

MIT
