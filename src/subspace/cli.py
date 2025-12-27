"""CLI router with nested subparsers for subspace commands."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from subspace import __version__, debug


CODEX_INTEGRATION_MARKER = "## Subspace Agent Tools"
CODEX_INTEGRATION_CONTENT = '''
## Subspace Agent Tools

You have access to the Subspace CLI (`subspace`) which provides two powerful capabilities:
1. **Subagents** - Run specialized agents in isolated sessions
2. **Slash Commands** - Execute predefined prompts/workflows programmatically

---

## Subspace Subagent System

Subagents run in isolated Codex sessions with their own context, preventing context window bloat.

### Recognizing Subagent Requests

When users reference `@agent-{name}` in their input, they want you to dispatch that subagent:

- `@agent-tdd-agent` → Run tdd-agent subagent
- `@agent-coder` → Run coder subagent
- `@agent-web-search-researcher` → Run web-search-researcher subagent

### Subagent Commands

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

### Subagent Example Usage

```bash
# User says: "Use @agent-tdd-agent to write tests for the auth module"
subspace subagent run tdd-agent "Write comprehensive tests for the auth module"

# User says: "Have @agent-coder implement this and @agent-tdd-agent write tests"
subspace subagent parallel coder:"Implement the user profile feature" tdd-agent:"Write tests for user profile"
```

---

## Subspace Slash Command System

Slash commands are predefined prompts stored as markdown files that you can retrieve and execute programmatically. This enables:
- **Nested workflows**: Meta-prompts that reference other commands
- **Reusable procedures**: Standard operating procedures as executable prompts
- **Dynamic pipelines**: Users can chain commands like "run /quick_tasks then /execute_sync"

### Recognizing Slash Command Requests

When users reference `/{command-name}` in their task, they want you to execute that command:

- `/quick_tasks` → Retrieve and execute the quick_tasks prompt
- `/execute_sync` → Retrieve and execute the execute_sync prompt
- `/validate` → Retrieve and execute the validate prompt

### Slash Command CLI

```bash
# Get the full prompt text for a command (primary use case)
subspace command get /command-name [arg1] [arg2] ...

# List all available commands
subspace command list

# Show command details and metadata
subspace command show /command-name
```

### How to Execute Slash Commands

When a user asks you to run slash commands, follow this workflow:

1. **Retrieve the prompt**: Use `subspace command get /command-name` to get the full prompt text
2. **Execute the instructions**: Follow the prompt instructions as if the user gave them directly
3. **Handle nested commands**: If the prompt references other `/commands`, retrieve and execute those too
4. **Continue the pipeline**: Move to the next command when done

### Slash Command Example Usage

```bash
# User says: "run /quick_tasks and then /execute_sync. When done, run /validate"

# Step 1: Get and execute the first command
subspace command get /quick_tasks
# (Follow the returned prompt instructions)

# Step 2: Get and execute the second command
subspace command get /execute_sync
# (Follow the returned prompt instructions - may contain nested /commands)

# Step 3: Get and execute the final command
subspace command get /validate
# (Follow the returned prompt instructions)
```

### Command Arguments

Commands can accept positional arguments. Use `$1`, `$2`, etc. in your command files:

```bash
# If /deploy command contains: "Deploy $1 to $2 environment"
subspace command get /deploy backend production
# Returns: "Deploy backend to production environment"
```

### Nested Commands (Meta-Prompts)

A command prompt can reference other commands. When you see `/other-command` in a prompt:
1. First complete any instructions before the nested command reference
2. Retrieve the nested command with `subspace command get /other-command`
3. Execute those instructions
4. Continue with any remaining instructions from the parent prompt

### Command Discovery

Commands are discovered from (in priority order):
1. Project-level `./.claude/commands/`
2. Project-level `./.codex/commands/`
3. User-level `~/.claude/commands/`
4. User-level `~/.codex/commands/`

---

## Output Handling

- **Text mode** (default): Returns human-readable output
- **JSON mode** (`--output json`): Returns structured JSON for programmatic use
- **JSONL mode** (`--output jsonl`): Streams events for UI integration (subagent only)

## Important Notes

- Subagents run in `workspace-write` sandbox mode for security
- Each subagent has fresh context (no access to this conversation)
- Provide complete, self-contained task descriptions
- Review subagent output before integrating changes
- Slash commands return prompt text that YOU execute - they don't run automatically
'''


def cmd_setup(args: argparse.Namespace) -> int:
    """Set up Codex CLI integration for subspace subagents."""
    codex_dir = Path.home() / ".codex"
    agents_file = codex_dir / "AGENTS.md"

    # Check if codex CLI is available
    codex_available = shutil.which("codex") is not None

    if not codex_available:
        print("Warning: 'codex' CLI not found in PATH", file=sys.stderr)
        print("Install it from: https://github.com/openai/codex", file=sys.stderr)
        print()

    # Create ~/.codex if it doesn't exist
    codex_dir.mkdir(parents=True, exist_ok=True)

    # Check if already installed
    if agents_file.exists():
        content = agents_file.read_text()
        if CODEX_INTEGRATION_MARKER in content:
            print(f"✓ Subspace integration already installed in {agents_file}")
            print()
            print("To reinstall, first remove the '## Subspace Subagent System' section.")
            return 0

    # Append subspace instructions
    with agents_file.open("a") as f:
        f.write(CODEX_INTEGRATION_CONTENT)

    print(f"✓ Subspace integration installed to {agents_file}")
    print()
    print("Codex will now recognize @agent-{{name}} syntax and can run subagents.")
    print()
    print("Try these commands:")
    print("  subspace subagent list          # See available agents")
    print("  subspace subagent show tdd-agent  # Show agent details")
    print()

    if not codex_available:
        print("Note: Install the Codex CLI to use 'subspace subagent run'")
        return 1

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run a single subagent, or vanilla Codex if no agent specified."""
    from subspace.core.discovery import find_agent, get_agent_sources
    from subspace.core.runner import run_agent, run_vanilla, validate_agent_name

    # Parse positional args: either [task] or [agent, task]
    positional = args.args
    if len(positional) == 1:
        # Vanilla mode: just task, no agent
        agent_name = None
        task = positional[0]
    elif len(positional) == 2:
        # Agent mode: agent + task
        agent_name = positional[0]
        task = positional[1]
    else:
        print("Error: Expected 1 or 2 arguments: [agent] <task>", file=sys.stderr)
        return 1

    if agent_name is None:
        # Vanilla Codex - no custom instructions
        debug("Running vanilla Codex (no agent)")
        return run_vanilla(
            task=task,
            output_format=args.output,
            timeout=args.timeout,
            enable_debug=args.debug,
        )

    # Security: Validate agent name to prevent path traversal
    try:
        validate_agent_name(agent_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Get agent sources (respects --agents-dir override)
    if args.agents_dir:
        from subspace.core.discovery import AgentSource
        from pathlib import Path
        sources = [AgentSource("override", Path(args.agents_dir).expanduser(), "override", 0)]
    else:
        sources = get_agent_sources()

    result = find_agent(agent_name, sources)
    if not result:
        print(f"Error: Agent '{agent_name}' not found", file=sys.stderr)
        return 1

    agent_path, source = result
    debug(f"Found agent: {agent_path} from {source.name}")

    return run_agent(
        agent_path=agent_path,
        task=task,
        output_format=args.output,
        timeout=args.timeout,
        enable_debug=args.debug,
    )


def cmd_parallel(args: argparse.Namespace) -> int:
    """Run multiple subagents in parallel."""
    from subspace.core.discovery import find_agent, get_agent_sources
    from subspace.core.runner import run_parallel

    # Get agent sources (respects --agents-dir override)
    if args.agents_dir:
        from subspace.core.discovery import AgentSource
        from pathlib import Path
        sources = [AgentSource("override", Path(args.agents_dir).expanduser(), "override", 0)]
    else:
        sources = get_agent_sources()

    return run_parallel(
        pairs=args.pairs,
        sources=sources,
        output_format=args.output,
        timeout=args.timeout,
        enable_debug=args.debug,
    )


def cmd_list(args: argparse.Namespace) -> int:
    """List available subagents."""
    from subspace.core.discovery import get_agent_sources, list_all_agents

    # Get agent sources (respects --agents-dir override)
    if args.agents_dir:
        from subspace.core.discovery import AgentSource
        from pathlib import Path
        sources = [AgentSource("override", Path(args.agents_dir).expanduser(), "override", 0)]
    else:
        sources = get_agent_sources()

    agents = list_all_agents(sources)

    if not agents:
        print("No agents found", file=sys.stderr)
        return 1

    if args.output == "json":
        import json
        print(json.dumps(agents, indent=2))
    else:
        # Table format: NAME, SOURCE, TYPE
        print(f"{'NAME':<20} {'SOURCE':<45} {'TYPE'}")
        print("-" * 80)
        for agent in agents:
            path_display = agent["path"]
            if len(path_display) > 42:
                path_display = "..." + path_display[-39:]
            print(f"{agent['name']:<20} {path_display:<45} {agent['source_type']}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show details of a specific subagent."""
    from subspace.core.discovery import find_agent, get_agent_sources, load_agent_details
    from subspace.core.runner import validate_agent_name

    # Security: Validate agent name to prevent path traversal
    try:
        validate_agent_name(args.agent)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Get agent sources (respects --agents-dir override)
    if args.agents_dir:
        from subspace.core.discovery import AgentSource
        from pathlib import Path
        sources = [AgentSource("override", Path(args.agents_dir).expanduser(), "override", 0)]
    else:
        sources = get_agent_sources()

    result = find_agent(args.agent, sources)
    if not result:
        print(f"Error: Agent '{args.agent}' not found", file=sys.stderr)
        return 1

    agent_path, source = result
    details = load_agent_details(agent_path, source)

    if args.output == "json":
        import json
        print(json.dumps(details, indent=2))
    else:
        print(f"Agent: {details['name']}")
        print(f"Source: {details['source']} ({details['source_type']})")
        print(f"Path: {details['path']}")
        print()
        if details.get("frontmatter"):
            print("Frontmatter:")
            for k, v in details["frontmatter"].items():
                print(f"  {k}: {v}")
            print()
        print("Instructions:")
        print("-" * 40)
        # Show first 50 lines
        lines = details.get("body", "").strip().split("\n")
        preview = "\n".join(lines[:50])
        print(preview)
        if len(lines) > 50:
            print(f"\n... ({len(lines) - 50} more lines)")

    return 0


# =============================================================================
# Slash Command Handlers
# =============================================================================


def cmd_command_get(args: argparse.Namespace) -> int:
    """Get the full prompt text for a slash command.

    This is the primary interface for agents to retrieve executable prompts.
    """
    from subspace.core.commands import (
        CommandSource,
        find_command,
        get_command_sources,
        interpolate_arguments,
        load_command_prompt,
        validate_command_name,
    )

    command_name = args.command
    command_args = args.args if args.args else []

    # Validate command name
    try:
        clean_name = validate_command_name(command_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Get command sources (respects --commands-dir override)
    if args.commands_dir:
        sources = [CommandSource("override", Path(args.commands_dir).expanduser(), "override", 0)]
    else:
        sources = get_command_sources()

    result = find_command(command_name, sources)
    if not result:
        print(f"Error: Command '/{clean_name}' not found", file=sys.stderr)
        return 1

    command_path, source = result
    debug(f"Found command: {command_path} from {source.name}")

    # Load and optionally interpolate the prompt
    prompt = load_command_prompt(command_path)

    if command_args:
        prompt = interpolate_arguments(prompt, command_args)

    if args.output == "json":
        import json
        print(json.dumps({
            "command": f"/{clean_name}",
            "path": str(command_path),
            "source": source.name,
            "args": command_args,
            "prompt": prompt,
        }, indent=2))
    else:
        # Raw prompt output - ready for agent execution
        print(prompt)

    return 0


def cmd_command_list(args: argparse.Namespace) -> int:
    """List available slash commands."""
    from subspace.core.commands import CommandSource, get_command_sources, list_all_commands

    # Get command sources (respects --commands-dir override)
    if args.commands_dir:
        sources = [CommandSource("override", Path(args.commands_dir).expanduser(), "override", 0)]
    else:
        sources = get_command_sources()

    commands = list_all_commands(sources)

    if not commands:
        print("No commands found", file=sys.stderr)
        print("\nCommands are discovered from:", file=sys.stderr)
        print("  - ./.claude/commands/", file=sys.stderr)
        print("  - ./.codex/commands/", file=sys.stderr)
        print("  - ~/.claude/commands/", file=sys.stderr)
        print("  - ~/.codex/commands/", file=sys.stderr)
        return 1

    if args.output == "json":
        import json
        print(json.dumps(commands, indent=2))
    else:
        # Table format: NAME, SOURCE, DESCRIPTION
        print(f"{'COMMAND':<25} {'SOURCE':<20} {'DESCRIPTION'}")
        print("-" * 80)
        for cmd in commands:
            desc = cmd.get("description", "")
            if len(desc) > 30:
                desc = desc[:27] + "..."
            print(f"{cmd['name']:<25} {cmd['source_type']:<20} {desc}")

    return 0


def cmd_command_show(args: argparse.Namespace) -> int:
    """Show details of a specific slash command."""
    from subspace.core.commands import (
        CommandSource,
        find_command,
        get_command_sources,
        load_command_details,
        validate_command_name,
    )

    command_name = args.command

    # Validate command name
    try:
        clean_name = validate_command_name(command_name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Get command sources (respects --commands-dir override)
    if args.commands_dir:
        sources = [CommandSource("override", Path(args.commands_dir).expanduser(), "override", 0)]
    else:
        sources = get_command_sources()

    result = find_command(command_name, sources)
    if not result:
        print(f"Error: Command '/{clean_name}' not found", file=sys.stderr)
        return 1

    command_path, source = result
    details = load_command_details(command_path, source)

    if args.output == "json":
        import json
        print(json.dumps(details, indent=2))
    else:
        print(f"Command: {details['name']}")
        print(f"Source: {details['source']} ({details['source_type']})")
        print(f"Path: {details['path']}")
        print()
        if details.get("frontmatter"):
            print("Frontmatter:")
            for k, v in details["frontmatter"].items():
                print(f"  {k}: {v}")
            print()
        print("Prompt:")
        print("-" * 40)
        # Show first 50 lines
        lines = details.get("body", "").strip().split("\n")
        preview = "\n".join(lines[:50])
        print(preview)
        if len(lines) > 50:
            print(f"\n... ({len(lines) - 50} more lines)")

    return 0


def main() -> int:
    """Main entry point for subspace CLI."""
    parser = argparse.ArgumentParser(
        prog="subspace",
        description="Subspace CLI tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # subspace setup
    setup_parser = subparsers.add_parser(
        "setup",
        help="Set up Codex CLI integration",
        description="Install Subspace integration into ~/.codex/AGENTS.md for Codex CLI",
    )
    setup_parser.set_defaults(func=cmd_setup)

    # subspace subagent ...
    subagent_parser = subparsers.add_parser(
        "subagent",
        help="Run Codex subagents",
        description="Run specialized Codex subagents using Claude Code agent definitions",
    )
    subagent_sub = subagent_parser.add_subparsers(
        dest="subagent_command",
        required=True,
    )

    # subspace subagent run [agent] <task>
    run_parser = subagent_sub.add_parser(
        "run",
        help="Run a single agent",
        description="Run a Codex subagent with a task. If agent is omitted, runs vanilla Codex.",
    )
    run_parser.add_argument(
        "args",
        nargs="+",
        metavar="[agent] task",
        help="Agent name and task, or just task for vanilla Codex",
    )
    run_parser.add_argument(
        "--output",
        choices=["text", "jsonl"],
        default="text",
        help="Output format (jsonl for UI streaming)",
    )
    run_parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds (default: 600)",
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    run_parser.add_argument(
        "--agents-dir",
        help="Override: use single directory instead of discovery",
    )
    run_parser.set_defaults(func=cmd_run)

    # subspace subagent parallel <agent:task>...
    parallel_parser = subagent_sub.add_parser(
        "parallel",
        help="Run multiple agents in parallel",
        description='Run multiple agents concurrently (e.g., tdd-agent:"task1" coder:"task2")',
    )
    parallel_parser.add_argument(
        "pairs",
        nargs="+",
        help='agent:task pairs (e.g., tdd-agent:"write tests")',
    )
    parallel_parser.add_argument(
        "--output",
        choices=["text", "jsonl"],
        default="text",
        help="Output format (jsonl for UI streaming)",
    )
    parallel_parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds (default: 600)",
    )
    parallel_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    parallel_parser.add_argument(
        "--agents-dir",
        help="Override: use single directory instead of discovery",
    )
    parallel_parser.set_defaults(func=cmd_parallel)

    # subspace subagent list
    list_parser = subagent_sub.add_parser(
        "list",
        help="List available agents",
        description="List all discovered agents with their sources",
    )
    list_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    list_parser.add_argument(
        "--agents-dir",
        help="Override: use single directory instead of discovery",
    )
    list_parser.set_defaults(func=cmd_list)

    # subspace subagent show <agent>
    show_parser = subagent_sub.add_parser(
        "show",
        help="Show agent details",
        description="Show details of a specific agent",
    )
    show_parser.add_argument("agent", help="Agent name")
    show_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    show_parser.add_argument(
        "--agents-dir",
        help="Override: use single directory instead of discovery",
    )
    show_parser.set_defaults(func=cmd_show)

    # =========================================================================
    # subspace command ...
    # =========================================================================
    command_parser = subparsers.add_parser(
        "command",
        help="Retrieve and manage slash commands",
        description="Retrieve slash command prompts for programmatic execution by agents",
    )
    command_sub = command_parser.add_subparsers(
        dest="command_subcommand",
        required=True,
    )

    # subspace command get /name [args...]
    cmd_get_parser = command_sub.add_parser(
        "get",
        help="Get the full prompt text for a command",
        description="Retrieve the prompt text for a slash command. This is the primary interface for agents.",
    )
    cmd_get_parser.add_argument(
        "command",
        help="Command name (e.g., /quick_tasks or quick_tasks)",
    )
    cmd_get_parser.add_argument(
        "args",
        nargs="*",
        help="Optional arguments to interpolate ($1, $2, etc.)",
    )
    cmd_get_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text for raw prompt)",
    )
    cmd_get_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    cmd_get_parser.add_argument(
        "--commands-dir",
        help="Override: use single directory instead of discovery",
    )
    cmd_get_parser.set_defaults(func=cmd_command_get)

    # subspace command list
    cmd_list_parser = command_sub.add_parser(
        "list",
        help="List available commands",
        description="List all discovered slash commands with their sources",
    )
    cmd_list_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    cmd_list_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    cmd_list_parser.add_argument(
        "--commands-dir",
        help="Override: use single directory instead of discovery",
    )
    cmd_list_parser.set_defaults(func=cmd_command_list)

    # subspace command show /name
    cmd_show_parser = command_sub.add_parser(
        "show",
        help="Show command details",
        description="Show details of a specific slash command including metadata",
    )
    cmd_show_parser.add_argument(
        "command",
        help="Command name (e.g., /quick_tasks or quick_tasks)",
    )
    cmd_show_parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    cmd_show_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    cmd_show_parser.add_argument(
        "--commands-dir",
        help="Override: use single directory instead of discovery",
    )
    cmd_show_parser.set_defaults(func=cmd_command_show)

    # Parse and execute
    args = parser.parse_args()

    # Enable debug mode globally if requested
    if hasattr(args, "debug") and args.debug:
        import subspace
        subspace.DEBUG = True
        debug(f"subspace v{__version__}")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
