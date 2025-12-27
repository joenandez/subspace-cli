"""Tests for subspace.core.commands module."""

import pytest
from pathlib import Path
import tempfile
import os


class TestValidateCommandName:
    """Tests for command name validation."""

    def test_valid_simple_name(self):
        """Simple alphanumeric names should be valid."""
        from subspace.core.commands import validate_command_name

        assert validate_command_name("quick_tasks") == "quick_tasks"
        assert validate_command_name("deploy") == "deploy"
        assert validate_command_name("test123") == "test123"

    def test_valid_name_with_slash(self):
        """Names with leading slash should be normalized."""
        from subspace.core.commands import validate_command_name

        assert validate_command_name("/quick_tasks") == "quick_tasks"
        assert validate_command_name("/deploy") == "deploy"

    def test_valid_name_with_hyphen(self):
        """Names with hyphens should be valid."""
        from subspace.core.commands import validate_command_name

        assert validate_command_name("quick-tasks") == "quick-tasks"
        assert validate_command_name("/my-command") == "my-command"

    def test_valid_name_with_underscore(self):
        """Names with underscores should be valid."""
        from subspace.core.commands import validate_command_name

        assert validate_command_name("quick_tasks") == "quick_tasks"
        assert validate_command_name("/my_command") == "my_command"

    def test_empty_name_raises(self):
        """Empty names should raise ValueError."""
        from subspace.core.commands import validate_command_name

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_command_name("")

    def test_only_slash_raises(self):
        """Just '/' should raise ValueError."""
        from subspace.core.commands import validate_command_name

        with pytest.raises(ValueError, match="cannot be just"):
            validate_command_name("/")

    def test_name_starting_with_hyphen_raises(self):
        """Names starting with hyphen should raise ValueError."""
        from subspace.core.commands import validate_command_name

        with pytest.raises(ValueError, match="cannot start with hyphen"):
            validate_command_name("-invalid")

    def test_invalid_characters_raises(self):
        """Names with invalid characters should raise ValueError."""
        from subspace.core.commands import validate_command_name

        with pytest.raises(ValueError, match="must contain only"):
            validate_command_name("../path/traversal")

        with pytest.raises(ValueError, match="must contain only"):
            validate_command_name("command with spaces")


class TestParseFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_parse_simple_frontmatter(self):
        """Should parse simple key-value frontmatter."""
        from subspace.core.commands import parse_frontmatter

        content = """---
description: A test command
author: Test Author
---

Command body here.
"""
        result = parse_frontmatter(content)
        assert result["description"] == "A test command"
        assert result["author"] == "Test Author"

    def test_parse_quoted_values(self):
        """Should strip quotes from values."""
        from subspace.core.commands import parse_frontmatter

        content = """---
description: "A quoted description"
name: 'single quoted'
---

Body.
"""
        result = parse_frontmatter(content)
        assert result["description"] == "A quoted description"
        assert result["name"] == "single quoted"

    def test_no_frontmatter(self):
        """Should return empty dict if no frontmatter."""
        from subspace.core.commands import parse_frontmatter

        content = "Just some markdown content."
        result = parse_frontmatter(content)
        assert result == {}

    def test_incomplete_frontmatter(self):
        """Should return empty dict if frontmatter is not closed."""
        from subspace.core.commands import parse_frontmatter

        content = """---
description: Incomplete
This is not closed properly.
"""
        result = parse_frontmatter(content)
        assert result == {}


class TestStripFrontmatter:
    """Tests for frontmatter stripping."""

    def test_strip_frontmatter(self):
        """Should remove frontmatter and return body."""
        from subspace.core.commands import strip_frontmatter

        content = """---
description: Test
---

Command body here.
"""
        result = strip_frontmatter(content)
        assert result.strip() == "Command body here."

    def test_no_frontmatter_unchanged(self):
        """Should return content unchanged if no frontmatter."""
        from subspace.core.commands import strip_frontmatter

        content = "Just content."
        result = strip_frontmatter(content)
        assert result == "Just content."


class TestInterpolateArguments:
    """Tests for argument interpolation."""

    def test_interpolate_positional_args(self):
        """Should replace $1, $2, etc. with arguments."""
        from subspace.core.commands import interpolate_arguments

        prompt = "Deploy $1 to $2 environment"
        args = ["backend", "production"]
        result = interpolate_arguments(prompt, args)
        assert result == "Deploy backend to production environment"

    def test_interpolate_all_args(self):
        """Should replace $@ with all arguments."""
        from subspace.core.commands import interpolate_arguments

        prompt = "Run tests for: $@"
        args = ["auth", "users", "api"]
        result = interpolate_arguments(prompt, args)
        assert result == "Run tests for: auth users api"

    def test_no_interpolation_without_args(self):
        """Should return prompt unchanged if no args."""
        from subspace.core.commands import interpolate_arguments

        prompt = "Simple prompt with $1"
        result = interpolate_arguments(prompt, [])
        assert result == "Simple prompt with $1"

    def test_partial_interpolation(self):
        """Should only replace args that are provided."""
        from subspace.core.commands import interpolate_arguments

        prompt = "Deploy $1 to $2 with $3"
        args = ["backend", "staging"]
        result = interpolate_arguments(prompt, args)
        assert result == "Deploy backend to staging with $3"


class TestCommandDiscovery:
    """Tests for command discovery from directories."""

    def test_find_command_in_project(self):
        """Should find command in project directory."""
        from subspace.core.commands import CommandSource, find_command

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create command file
            commands_dir = Path(tmpdir) / ".claude" / "commands"
            commands_dir.mkdir(parents=True)
            (commands_dir / "test_cmd.md").write_text("Test command content")

            sources = [CommandSource("test", commands_dir, "project", 1)]
            result = find_command("test_cmd", sources)

            assert result is not None
            path, source = result
            assert path.name == "test_cmd.md"
            assert source.name == "test"

    def test_find_command_with_slash_prefix(self):
        """Should find command when name has leading slash."""
        from subspace.core.commands import CommandSource, find_command

        with tempfile.TemporaryDirectory() as tmpdir:
            commands_dir = Path(tmpdir) / ".claude" / "commands"
            commands_dir.mkdir(parents=True)
            (commands_dir / "deploy.md").write_text("Deploy content")

            sources = [CommandSource("test", commands_dir, "project", 1)]
            result = find_command("/deploy", sources)

            assert result is not None
            path, _ = result
            assert path.name == "deploy.md"

    def test_command_not_found(self):
        """Should return None if command not found."""
        from subspace.core.commands import CommandSource, find_command

        with tempfile.TemporaryDirectory() as tmpdir:
            commands_dir = Path(tmpdir)
            sources = [CommandSource("test", commands_dir, "project", 1)]
            result = find_command("nonexistent", sources)

            assert result is None

    def test_priority_ordering(self):
        """Should respect source priority (lower = higher priority)."""
        from subspace.core.commands import CommandSource, find_command

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two command directories
            project_dir = Path(tmpdir) / "project" / ".claude" / "commands"
            user_dir = Path(tmpdir) / "user" / ".claude" / "commands"
            project_dir.mkdir(parents=True)
            user_dir.mkdir(parents=True)

            # Same command in both
            (project_dir / "deploy.md").write_text("Project deploy")
            (user_dir / "deploy.md").write_text("User deploy")

            sources = [
                CommandSource("project", project_dir, "project", 1),
                CommandSource("user", user_dir, "user", 2),
            ]
            result = find_command("deploy", sources)

            assert result is not None
            path, source = result
            assert source.name == "project"  # Higher priority (lower number)


class TestListAllCommands:
    """Tests for listing all commands."""

    def test_list_all_commands(self):
        """Should list all commands from all sources."""
        from subspace.core.commands import CommandSource, list_all_commands

        with tempfile.TemporaryDirectory() as tmpdir:
            commands_dir = Path(tmpdir) / ".claude" / "commands"
            commands_dir.mkdir(parents=True)

            (commands_dir / "cmd1.md").write_text("""---
description: First command
---

Body 1
""")
            (commands_dir / "cmd2.md").write_text("Body 2 no frontmatter")

            sources = [CommandSource("test", commands_dir, "project", 1)]
            commands = list_all_commands(sources)

            assert len(commands) == 2
            names = [c["name"] for c in commands]
            assert "/cmd1" in names
            assert "/cmd2" in names

            # Check description from frontmatter
            cmd1 = next(c for c in commands if c["name"] == "/cmd1")
            assert cmd1["description"] == "First command"

    def test_list_deduplicates_by_name(self):
        """Should only include first occurrence of duplicate names."""
        from subspace.core.commands import CommandSource, list_all_commands

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            user_dir = Path(tmpdir) / "user"
            project_dir.mkdir(parents=True)
            user_dir.mkdir(parents=True)

            (project_dir / "deploy.md").write_text("Project version")
            (user_dir / "deploy.md").write_text("User version")

            sources = [
                CommandSource("project", project_dir, "project", 1),
                CommandSource("user", user_dir, "user", 2),
            ]
            commands = list_all_commands(sources)

            deploy_commands = [c for c in commands if c["name"] == "/deploy"]
            assert len(deploy_commands) == 1
            assert deploy_commands[0]["source"] == "project"


class TestLoadCommandPrompt:
    """Tests for loading command prompt text."""

    def test_load_command_prompt(self):
        """Should load prompt text without frontmatter."""
        from subspace.core.commands import load_command_prompt

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "test.md"
            cmd_file.write_text("""---
description: Test
---

This is the prompt text.
Do something useful.
""")
            result = load_command_prompt(cmd_file)
            assert "This is the prompt text." in result
            assert "Do something useful." in result
            assert "description:" not in result

    def test_load_command_prompt_no_frontmatter(self):
        """Should load full content if no frontmatter."""
        from subspace.core.commands import load_command_prompt

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "test.md"
            cmd_file.write_text("Just a simple prompt.")

            result = load_command_prompt(cmd_file)
            assert result == "Just a simple prompt."


class TestCommandSources:
    """Tests for get_command_sources."""

    def test_get_command_sources_finds_project_dirs(self):
        """Should find command directories in project root."""
        from subspace.core.commands import get_command_sources

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            claude_commands = project_root / ".claude" / "commands"
            codex_commands = project_root / ".codex" / "commands"
            claude_commands.mkdir(parents=True)
            codex_commands.mkdir(parents=True)

            # Change to project directory
            old_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                sources = get_command_sources(project_root)

                source_names = [s.name for s in sources]
                assert "claude_project" in source_names
                assert "codex_project" in source_names
            finally:
                os.chdir(old_cwd)

    def test_get_command_sources_empty_if_no_dirs(self):
        """Should return empty list if no command directories exist."""
        from subspace.core.commands import get_command_sources

        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create any command directories
            sources = get_command_sources(Path(tmpdir))
            # Filter to only project sources (user dirs might exist)
            project_sources = [s for s in sources if s.source_type == "project"]
            assert len(project_sources) == 0


class TestCliModuleImportsCommands:
    """Tests that command-related CLI functions can be imported."""

    def test_import_commands_module(self):
        """Commands module should import successfully."""
        from subspace.core import commands
        assert hasattr(commands, "find_command")
        assert hasattr(commands, "list_all_commands")
        assert hasattr(commands, "get_command_sources")
        assert hasattr(commands, "load_command_prompt")
        assert hasattr(commands, "interpolate_arguments")

    def test_import_cli_command_handlers(self):
        """CLI should have command handler functions."""
        from subspace import cli
        assert hasattr(cli, "cmd_command_get")
        assert hasattr(cli, "cmd_command_list")
        assert hasattr(cli, "cmd_command_show")
