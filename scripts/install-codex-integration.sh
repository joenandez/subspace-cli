#!/bin/bash
# Install Subspace subagent integration for Codex CLI
# Appends instructions to ~/.codex/AGENTS.md

set -e

CODEX_DIR="$HOME/.codex"
AGENTS_FILE="$CODEX_DIR/AGENTS.md"
MARKER="## Subspace Subagent System"

# Create ~/.codex if it doesn't exist
mkdir -p "$CODEX_DIR"

# Check if already installed
if [ -f "$AGENTS_FILE" ] && grep -q "$MARKER" "$AGENTS_FILE"; then
    echo "Subspace integration already installed in $AGENTS_FILE"
    echo "To reinstall, remove the '$MARKER' section first."
    exit 0
fi

# Append subspace instructions
cat >> "$AGENTS_FILE" << 'EOF'

## Subspace Subagent System

You have access to specialized subagents via the `subspace subagent` CLI. Subagents run in isolated Codex sessions with their own context, preventing context window bloat.

### Recognizing Subagent Requests

When users reference `@agent-{name}` in their input, they want you to dispatch that subagent:

- `@agent-tdd-agent` → Run tdd-agent subagent
- `@agent-coder` → Run coder subagent
- `@agent-web-search-researcher` → Run web-search-researcher subagent

### Available Commands

```bash
# List all available subagents
subspace subagent list

# Show details about a specific agent
subspace subagent show <agent-name>

# Run a single subagent with a task
subspace subagent run <agent-name> "<task description>"

# Run multiple subagents in parallel
subspace subagent parallel <agent>:"<task>" [<agent>:"<task>" ...]
```

### When to Use Subagents

Use subagents when:
- User explicitly requests one with `@agent-{name}` syntax
- Task benefits from specialized expertise (TDD, research, code review)
- You want to isolate complex work from the main context
- Running parallel independent tasks

### Example Usage

```bash
# User says: "Use @agent-tdd-agent to write tests for the auth module"
subspace subagent run tdd-agent "Write comprehensive tests for the auth module"

# User says: "Have @agent-coder implement this and @agent-tdd-agent write tests"
subspace subagent parallel coder:"Implement the user profile feature" tdd-agent:"Write tests for user profile"

# Check what agents are available
subspace subagent list
```

### Output Handling

- **Text mode** (default): Returns the final agent response
- **JSONL mode** (`--output jsonl`): Streams events for UI integration

### Important Notes

- Subagents run in `workspace-write` sandbox mode for security
- Each subagent has fresh context (no access to this conversation)
- Provide complete, self-contained task descriptions
- Review subagent output before integrating changes
EOF

echo "✓ Subspace integration installed to $AGENTS_FILE"
echo ""
echo "Codex will now recognize @agent-{name} syntax and can run subagents."
echo "Try: subspace subagent list"
