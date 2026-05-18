#!/usr/bin/env python3
"""Test CLI tool calling functionality."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import SimpleCLI


async def test_tool_calls():
    """Test tool calling functionality."""
    cli = SimpleCLI()
    
    # Test list files
    print("=== Testing Tool Call: List Directory ===")
    response = await cli.process_message("list files in current directory")
    print(f"Response: {response}\n")
    
    # Test read file
    print("=== Testing Tool Call: Read File ===")
    response = await cli.process_message("read the main.py file")
    print(f"Response: {response}\n")
    
    # Test normal conversation
    print("=== Testing Normal Conversation ===")
    response = await cli.process_message("What can you do?")
    print(f"Response: {response}\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tool_calls())
