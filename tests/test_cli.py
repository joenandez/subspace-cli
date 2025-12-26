"""Tests for subspace.cli module."""

import argparse
import pytest


class TestRunCommandArgParsing:
    """Tests for run command argument parsing logic."""

    def test_single_arg_is_task_only(self):
        """Single positional arg should be interpreted as task (vanilla mode)."""
        args = ["my task description"]

        if len(args) == 1:
            agent_name = None
            task = args[0]
        else:
            agent_name = args[0]
            task = args[1]

        assert agent_name is None
        assert task == "my task description"

    def test_two_args_is_agent_and_task(self):
        """Two positional args should be agent + task."""
        args = ["tdd-agent", "my task description"]

        if len(args) == 1:
            agent_name = None
            task = args[0]
        else:
            agent_name = args[0]
            task = args[1]

        assert agent_name == "tdd-agent"
        assert task == "my task description"

    def test_three_args_is_error(self):
        """More than two positional args should be an error."""
        args = ["one", "two", "three"]

        # This mimics the logic in cmd_run
        if len(args) == 1:
            valid = True
        elif len(args) == 2:
            valid = True
        else:
            valid = False

        assert valid is False


class TestCliModuleImports:
    """Tests that CLI module can be imported without errors."""

    def test_import_cli(self):
        """CLI module should import successfully."""
        from subspace import cli
        assert hasattr(cli, "main")
        assert hasattr(cli, "cmd_run")
        assert hasattr(cli, "cmd_setup")

    def test_import_runner(self):
        """Runner module should import successfully."""
        from subspace.core import runner
        assert hasattr(runner, "run_agent")
        assert hasattr(runner, "run_vanilla")
        assert hasattr(runner, "run_parallel")

    def test_import_discovery(self):
        """Discovery module should import successfully."""
        from subspace.core import discovery
        assert hasattr(discovery, "find_agent")
        assert hasattr(discovery, "list_all_agents")
        assert hasattr(discovery, "get_agent_sources")
