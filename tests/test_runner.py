"""Tests for subspace.core.runner module."""

import pytest

from subspace.core.runner import (
    extract_agent_messages,
    validate_agent_name,
    parse_agent_task_pair,
    build_payload,
    build_vanilla_payload,
)


class TestValidateAgentName:
    """Tests for agent name validation (security)."""

    def test_valid_names(self):
        """Valid agent names should pass validation."""
        valid_names = [
            "tdd-agent",
            "coder",
            "web_search_researcher",
            "agent123",
            "MyAgent",
            "a",
        ]
        for name in valid_names:
            validate_agent_name(name)  # Should not raise

    def test_empty_name_rejected(self):
        """Empty names should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_agent_name("")

    def test_path_traversal_rejected(self):
        """Path traversal attempts should be rejected."""
        dangerous_names = [
            "../etc/passwd",
            "..\\windows\\system32",
            "agent/../secret",
            "./hidden",
        ]
        for name in dangerous_names:
            with pytest.raises(ValueError, match="must contain only"):
                validate_agent_name(name)

    def test_special_chars_rejected(self):
        """Special characters should be rejected."""
        invalid_names = [
            "agent name",  # space
            "agent@name",  # @
            "agent/name",  # /
            "agent.name",  # .
            "agent:name",  # :
        ]
        for name in invalid_names:
            with pytest.raises(ValueError, match="must contain only"):
                validate_agent_name(name)

    def test_leading_hyphen_rejected(self):
        """Names starting with hyphen should be rejected."""
        with pytest.raises(ValueError, match="cannot start with hyphen"):
            validate_agent_name("-dangerous")


class TestExtractAgentMessages:
    """Tests for JSONL parsing and message extraction."""

    def test_single_agent_message(self):
        """Extract single agent message from JSONL."""
        jsonl_lines = [
            '{"type":"thread.started","thread_id":"123"}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"Hello world"}}',
            '{"type":"turn.completed"}',
        ]
        result = extract_agent_messages(jsonl_lines)
        assert result == "Hello world"

    def test_multiple_agent_messages(self):
        """Multiple agent messages should be joined with double newlines."""
        jsonl_lines = [
            '{"type":"item.completed","item":{"type":"agent_message","text":"First message"}}',
            '{"type":"item.completed","item":{"type":"reasoning","text":"thinking..."}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"Second message"}}',
        ]
        result = extract_agent_messages(jsonl_lines)
        assert result == "First message\n\nSecond message"

    def test_ignores_non_agent_messages(self):
        """Non-agent_message items should be ignored."""
        jsonl_lines = [
            '{"type":"thread.started"}',
            '{"type":"item.completed","item":{"type":"reasoning","text":"thinking"}}',
            '{"type":"item.completed","item":{"type":"command_execution","command":"ls"}}',
            '{"type":"turn.completed"}',
        ]
        result = extract_agent_messages(jsonl_lines)
        assert result == ""

    def test_handles_empty_input(self):
        """Empty input should return empty string."""
        assert extract_agent_messages([]) == ""

    def test_handles_malformed_json(self):
        """Malformed JSON lines should be skipped."""
        jsonl_lines = [
            "not json",
            '{"type":"item.completed","item":{"type":"agent_message","text":"Valid"}}',
            "{broken",
        ]
        result = extract_agent_messages(jsonl_lines)
        assert result == "Valid"

    def test_handles_empty_text(self):
        """Agent messages with empty text should be skipped."""
        jsonl_lines = [
            '{"type":"item.completed","item":{"type":"agent_message","text":""}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"Real message"}}',
        ]
        result = extract_agent_messages(jsonl_lines)
        assert result == "Real message"


class TestParseAgentTaskPair:
    """Tests for agent:task parsing."""

    def test_simple_format(self):
        """Parse simple agent:task format."""
        agent, task = parse_agent_task_pair("tdd-agent:write tests")
        assert agent == "tdd-agent"
        assert task == "write tests"

    def test_double_quoted_task(self):
        """Parse agent:"task with spaces" format."""
        agent, task = parse_agent_task_pair('coder:"implement the feature"')
        assert agent == "coder"
        assert task == "implement the feature"

    def test_single_quoted_task(self):
        """Parse agent:'task with spaces' format."""
        agent, task = parse_agent_task_pair("coder:'implement the feature'")
        assert agent == "coder"
        assert task == "implement the feature"

    def test_invalid_format_no_colon(self):
        """Missing colon should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid agent:task format"):
            parse_agent_task_pair("invalid format")

    def test_empty_task_rejected(self):
        """Empty task should be rejected."""
        with pytest.raises(ValueError, match="Task cannot be empty"):
            parse_agent_task_pair("agent:")

    def test_invalid_agent_name_rejected(self):
        """Invalid agent names should be rejected."""
        with pytest.raises(ValueError, match="must contain only"):
            parse_agent_task_pair("../passwd:hack")


class TestBuildPayload:
    """Tests for payload building."""

    def test_build_payload_structure(self):
        """Payload should have correct structure."""
        payload = build_payload("test-agent", "Do something", "my task")

        assert "instructions" in payload
        assert "task" in payload
        assert "metadata" in payload
        assert payload["task"] == "my task"
        assert payload["metadata"]["agentName"] == "test-agent"
        assert "startedAt" in payload["metadata"]

    def test_payload_includes_guidance(self):
        """Payload instructions should include guidance block."""
        payload = build_payload("test-agent", "Custom instructions", "task")

        assert "You ARE the test-agent agent" in payload["instructions"]
        assert "Do NOT spawn subagents" in payload["instructions"]
        assert "Custom instructions" in payload["instructions"]


class TestBuildVanillaPayload:
    """Tests for vanilla payload building."""

    def test_vanilla_payload_structure(self):
        """Vanilla payload should have minimal structure."""
        payload = build_vanilla_payload("my task")

        assert payload["task"] == "my task"
        assert payload["metadata"]["agentName"] == "codex"
        assert "instructions" not in payload

    def test_vanilla_payload_no_instructions(self):
        """Vanilla payload should not have instructions field."""
        payload = build_vanilla_payload("task")
        assert "instructions" not in payload
