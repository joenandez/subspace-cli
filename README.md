# subspace-agent

Subspace CLI - run Codex subagents and slash commands programmatically.

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

This installs the Subspace integration into `~/.codex/AGENTS.md` so Codex can recognize `@agent-{name}` and `/command` syntax.

## Requirements

- Python 3.10+
- OpenAI Codex CLI installed (`codex` command) - for subagent run/parallel commands

## Features

Subspace provides two main capabilities:

1. **Subagents** - Run specialized agents in isolated Codex sessions
2. **Slash Commands** - Retrieve and execute predefined prompts programmatically

---

## Subagents

Run specialized Codex subagents with their own isolated context.

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

### Agent Discovery

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

---

## Slash Commands

Retrieve slash command prompts for programmatic execution by agents. This enables:
- **Nested workflows**: Meta-prompts that reference other commands
- **Reusable procedures**: Standard operating procedures as executable prompts
- **Dynamic pipelines**: Chain commands like "run /quick_tasks then /execute_sync"

### Get a command prompt (primary use case)

```bash
subspace command get /command-name [args...]
```

This returns the full prompt text that an agent can then execute.

**Basic usage:**
```bash
subspace command get /quick_tasks
```

**With arguments (interpolates $1, $2, etc.):**
```bash
subspace command get /deploy backend production
# If command contains "Deploy $1 to $2", returns "Deploy backend to production"
```

### List available commands

```bash
subspace command list
```

### Show command details

```bash
subspace command show /quick_tasks
```

### JSON output

```bash
subspace command get /quick_tasks --output json
subspace command list --output json
```

### Command Discovery

Commands are discovered from multiple sources in priority order:

1. Project-level `./.claude/commands/`
2. Project-level `./.codex/prompts/`
3. User-level `~/.claude/commands/`
4. User-level `~/.codex/prompts/`

Override with `--commands-dir`:

```bash
subspace command list --commands-dir ~/my-commands
```

### Creating Commands

Commands are markdown files with optional YAML frontmatter:

```markdown
---
description: Run quick validation tasks
---

Please perform the following quick validation tasks:

1. Run the linter: `npm run lint`
2. Run unit tests: `npm test`
3. Check for TypeScript errors: `npx tsc --noEmit`

Report any issues found.
```

Save this as `.claude/commands/quick_tasks.md` and it becomes available as `/quick_tasks`.

### Nested Commands (Meta-Prompts)

Commands can reference other commands. When an agent sees `/other-command` in a prompt, it should:

1. Complete instructions before the reference
2. Retrieve the nested command with `subspace command get /other-command`
3. Execute those instructions
4. Continue with remaining parent prompt instructions

Example meta-prompt (`.claude/commands/full_review.md`):

```markdown
---
description: Complete code review workflow
---

First, run /quick_tasks to ensure basic validation passes.

Then, perform a detailed code review:
1. Check for security issues
2. Review error handling
3. Verify test coverage

Finally, run /generate_report to summarize findings.
```

---

## Example: Agent Workflow with Commands

When a user says: "run /quick_tasks and then /execute_sync. When done, run /validate"

An agent using Subspace would:

```bash
# Step 1: Get and execute first command
subspace command get /quick_tasks
# (Agent follows the returned prompt instructions)

# Step 2: Get and execute second command
subspace command get /execute_sync
# (Agent follows instructions - may contain nested /commands)

# Step 3: Get and execute final command
subspace command get /validate
# (Agent follows the returned prompt instructions)
```

---

## Debug Mode

Enable debug output for any command:

```bash
subspace subagent run tdd-agent "task" --debug
subspace command get /quick_tasks --debug
```

## License

MIT
