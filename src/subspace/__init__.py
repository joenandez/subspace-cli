"""Subspace CLI - run Codex subagents and more."""

__version__ = "0.1.0"

# Debug flag for verbose output
DEBUG = False


def debug(*args, **kwargs) -> None:
    """Print debug message if DEBUG is enabled."""
    if DEBUG:
        import sys
        print("[DEBUG]", *args, file=sys.stderr, **kwargs)
