# Quick Tasks — Subspace CLI Package

*Created by: quick_tasks.md on 2025-12-22*
*Updated: 2025-12-22 (simplified per plan review)*

## Objective

Create installable `subspace-agent` Python package with `subspace subagent` CLI for running Codex subagents with JSONL streaming output and multi-source agent discovery.

## Scope

- **In Scope:**
  - Package structure (`src/subspace/`) - refactored from working prototype
  - `pyproject.toml` with CLI entry point
  - CLI router with nested subparsers
  - Multi-source agent discovery (Claude Code, Codex, plugins)
  - `subspace subagent run` with JSONL streaming
  - `subspace subagent parallel` with agent_id tagging
  - `subspace subagent list/show` with source display
  - `--debug` mode (inline, no separate module)
  - Local `pip install -e .` validation

- **Out of Scope (Deferred to Phase 2):**
  - Config file support (`~/.config/subspace/config.toml`)
  - Extra paths / disable sources config
  - Environment variable configuration
  - `--output json` (use `jsonl | jq -s` instead)
  - PyPI publication
  - Homebrew formula
  - Standalone binaries
  - `subspace memory` command
  - `subspace sync` command

## Simplifications Applied

1. **Start from prototype** - Refactor `scripts/run_subagent.py`, don't rewrite
2. **Consolidated modules** - `core/` has 2 files: `runner.py` + `discovery.py`
3. **Inline debug logging** - No separate `utils/logging.py`
4. **Two output formats** - `text` and `jsonl` only (no `json`)
5. **Deferred config** - Use CLI flags; config file comes in Phase 2

## Tasks

## Phase 1: Package Foundation

### [1.1] Create package from prototype
- [x] **1.1.1** Copy and restructure `scripts/run_subagent.py` into package
  - [x] Create `src/subspace/` directory with `__init__.py`
  - [x] Create `__main__.py` for `python -m subspace` execution
  - [x] Extract CLI logic into `cli.py`

- [x] **1.1.2** Create `pyproject.toml` with package metadata
  - [x] Package name `subspace-agent`, version `0.1.0`
  - [x] Entry point `subspace = "subspace.cli:main"`
  - [x] `requires-python = ">=3.10"` with no external dependencies

### [1.2] Implement CLI router with nested subparsers
- [x] **1.2.1** Refactor CLI to use subcommand structure
  - [x] `subspace --version` returns version string
  - [x] `subspace subagent --help` shows run/parallel/list/show
  - [x] Structure supports future command groups (`memory`, `sync`)

- [x] **1.2.2** Wire subcommand arguments
  - [x] `run`: agent, task, --output (text/jsonl), --timeout, --debug, --agents-dir
  - [x] `parallel`: pairs, --output, --timeout, --debug, --agents-dir
  - [x] `list`: --output (text/json), --agents-dir
  - [x] `show`: agent, --output (text/json), --agents-dir

## Phase 2: Agent Discovery

### [2.1] Implement multi-source agent discovery
- [x] **2.1.1** Create `core/discovery.py` with source hierarchy
  - [x] AgentSource dataclass with name, path, source_type, priority
  - [x] `get_agent_sources()` returns sources in priority order
  - [x] Sources filtered to only those that exist on disk

- [x] **2.1.2** Implement all discovery sources
  - [x] Project-level `./.claude/agents/` (priority 1)
  - [x] Project-level `./.codex/agents/` (priority 2)
  - [x] User-level `~/.claude/agents/` (priority 3)
  - [x] User-level `~/.codex/agents/` (priority 4)
  - [x] Plugin agents from `~/.claude/plugins/installed_plugins.json` (priority 5)

- [x] **2.1.3** Implement find and list functions
  - [x] `find_agent(name)` returns first match respecting priority
  - [x] `list_all_agents()` returns all agents, first-match wins for duplicates
  - [x] `--agents-dir` bypasses discovery when specified

## Phase 3: Core Execution

### [3.1] Implement subspace subagent run command
- [x] **3.1.1** Port sandbox/credential sync from prototype
  - [x] Credentials synced to `.subspace/codex-subagent/`
  - [x] `config.toml` and `auth.json` copied if present

- [x] **3.1.2** Implement agent loading with frontmatter stripping
  - [x] Agent markdown loaded from discovered path
  - [x] YAML frontmatter stripped (between `---` markers)
  - [x] Guidance block added to prevent recursive spawning

- [x] **3.1.3** Implement Codex execution with JSONL streaming
  - [x] `codex exec --sandbox workspace-write --json` invoked
  - [x] `--output text`: pass through raw output
  - [x] `--output jsonl`: stream native Codex events (no buffering)
  - [x] Timeout kills process after `--timeout` seconds (default 600)

- [x] **3.1.4** Implement inline debug output
  - [x] `--debug` prints to stderr with `[DEBUG]` prefix
  - [x] Logs: version, agent path, credential sync, command, pid, exit code, duration

### [3.2] Implement subspace subagent parallel command
- [x] **3.2.1** Parse and validate agent:task pairs
  - [x] `agent:"task"` format parsed correctly
  - [x] Validation error if pair format invalid

- [x] **3.2.2** Implement parallel execution with asyncio
  - [x] Each agent runs in separate asyncio subprocess
  - [x] All agents started concurrently
  - [x] Results collected as agents complete

- [x] **3.2.3** Implement JSONL event tagging
  - [x] Each event wrapped with `agent_id` and `agent_name`
  - [x] `agent_id` format: `{agent_name}-{index}` (e.g., `tdd-agent-0`)
  - [x] Events interleaved as they arrive

## Phase 4: List/Show Commands

### [4.1] Implement list and show commands
- [x] **4.1.1** Implement `subspace subagent list`
  - [x] Text: table with NAME, SOURCE, TYPE columns
  - [x] JSON: array of agent objects with all fields

- [x] **4.1.2** Implement `subspace subagent show`
  - [x] Text: name, source, path, description (from frontmatter), preview
  - [x] JSON: full metadata as object

## Phase 5: Manual Validation

### [5.1] Validate local pip install workflow
- [x] **5.1.1** Verify installation
  - [x] `pip install -e .` succeeds
  - [x] `subspace` command available in PATH
  - [x] `subspace --version` returns correct version

- [x] **5.1.2** Verify all subcommands work
  - [x] `subspace subagent list` shows discovered agents with sources
  - [x] `subspace subagent show <agent>` displays details
  - [ ] `subspace subagent run <agent> "task"` executes (not tested with real Codex)
  - [ ] `subspace subagent parallel` runs multiple agents (not tested with real Codex)

- [ ] **5.1.3** Verify JSONL streaming
  - [ ] `--output jsonl` streams events in real-time (requires Codex)
  - [ ] Parallel output includes agent_id tagging (requires Codex)
  - [ ] Events parseable as valid JSON lines (requires Codex)

## Package Structure

```
subspace-agent/
├── pyproject.toml
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

## Parallelization Strategy

**Wave 1 (Parallel)**: 1.1, 1.2
- Rationale: Package setup and CLI structure are independent

**Wave 2 (Parallel)**: 2.1, 3.1
- Rationale: Discovery and execution can be built in parallel

**Wave 3 (Sequential)**: 3.2
- Rationale: Parallel execution depends on single-agent run

**Wave 4 (Parallel)**: 4.1
- Rationale: List/show are independent once discovery exists

**Wave 5 (Sequential)**: 5.1
- Rationale: Validation requires all features complete

## Summary

- **5 phases** (down from 6)
- **8 parent tasks** (down from 10)
- **17 sub-tasks** (down from 24)
- **Deferred:** Config file support, `--output json`, separate logging module
- **Kept:** Plugin discovery (important for subagent ecosystem)
