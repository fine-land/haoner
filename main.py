#!/usr/bin/env python3
"""Main entry point for the Haoner project."""

import sys
import os

# Ensure proper path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Run the CLI."""
    from cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
