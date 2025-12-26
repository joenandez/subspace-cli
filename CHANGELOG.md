# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-26

### Added

- **Core CLI commands**
  - `subspace subagent run [agent] <task>` - Run a single agent or vanilla Codex
  - `subspace subagent parallel <agent:task>...` - Run multiple agents concurrently
  - `subspace subagent list` - List all discovered agents
  - `subspace subagent show <agent>` - Show agent details
  - `subspace setup` - Install Codex CLI integration

- **Vanilla mode** - Run Codex without custom agent instructions by omitting the agent argument

- **Multi-source agent discovery**
  - Project-level: `./.claude/agents/`, `./.codex/agents/`
  - User-level: `~/.claude/agents/`, `~/.codex/agents/`
  - Plugin agents from `~/.claude/plugins/*/agents/`

- **Parallel execution** with asyncio for true concurrency

- **Output formats**
  - Text mode (default): Human-readable output
  - JSONL mode: Real-time event streaming for UI integration

- **Security features**
  - Agent name validation (prevents path traversal)
  - Symlink rejection in credential sync
  - Sandbox mode (`workspace-write`) for all executions

- **Codex CLI integration** via `subspace setup` command

### Technical Details

- Always uses `codex exec --json` internally for reliable structured output
- Parses JSONL events to extract `agent_message` items for text mode
- Credential sync from `~/.codex/` to `.subspace/codex-subagent/` for sandbox mode
