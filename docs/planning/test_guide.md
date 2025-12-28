# Manual Test Guide: Subspace CLI Package

*Generated: 2025-12-22*

## Prerequisites

- Python 3.10+
- OpenAI Codex CLI installed (`codex` command available) - only needed for run/parallel commands
- Agent files in `~/.claude/agents/` or other discovery paths

## Installation

```bash
cd subspace-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Test Cases

### 1. Version Check
```bash
subspace --version
```
**Expected:** `subspace 0.1.0`

### 2. Help Output
```bash
subspace --help
subspace subagent --help
```
**Expected:** Shows available commands and options

### 3. List Agents
```bash
subspace subagent list
```
**Expected:** Table with NAME, SOURCE, TYPE columns showing discovered agents

### 4. List Agents (JSON format)
```bash
subspace subagent list --output json
```
**Expected:** JSON array of agent objects with name, path, source, source_type fields

### 5. Show Agent Details
```bash
subspace subagent show tdd-agent
```
**Expected:** Agent name, source, path, frontmatter, and instruction preview

### 6. Path Traversal Prevention
```bash
subspace subagent show "../../../etc/passwd"
```
**Expected:** Error message about invalid agent name

### 7. Run Single Agent (requires Codex)
```bash
subspace subagent run tdd-agent "say hello" --timeout 30
```
**Expected:** Agent response after Codex execution

### 8. Run with JSONL Output (requires Codex)
```bash
subspace subagent run tdd-agent "say hello" --output jsonl
```
**Expected:** Streaming JSONL events, final complete event

### 9. Debug Mode
```bash
subspace subagent list --debug
```
**Note:** --debug only applies to run/parallel commands

```bash
subspace subagent run tdd-agent "say hello" --debug
```
**Expected:** [DEBUG] prefixed messages on stderr

### 10. Override Agents Directory
```bash
subspace subagent list --agents-dir ~/.claude/agents
```
**Expected:** Only shows agents from specified directory

### 11. Parallel Execution (requires Codex)
```bash
subspace subagent parallel tdd-agent:"task 1" tdd-agent:"task 2" --timeout 60
```
**Expected:** Both agents run concurrently, results streamed as they complete

## Validation Status

| Test | Status | Notes |
|------|--------|-------|
| Version check | ✅ Passed | Tested during development |
| Help output | ✅ Passed | Tested during development |
| List agents | ✅ Passed | Shows user + plugin agents |
| List JSON | ✅ Passed | Valid JSON output |
| Show agent | ✅ Passed | Shows details correctly |
| Path traversal | ✅ Passed | Blocks invalid names |
| Run single | ⏳ Pending | Requires Codex CLI |
| Run JSONL | ⏳ Pending | Requires Codex CLI |
| Debug mode | ⏳ Pending | Requires Codex CLI |
| Agents dir | ✅ Passed | Override works |
| Parallel | ⏳ Pending | Requires Codex CLI |

## Known Limitations

1. **Requires Codex CLI**: Run and parallel commands need working `codex` binary
2. **No tests**: Unit test suite not yet implemented
3. **Debug output**: Some debug messages less detailed than spec (cosmetic)
