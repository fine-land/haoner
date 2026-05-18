"""Terminal Tool Module - Execute shell commands."""

import subprocess
import json

from .registry import registry, tool_error, tool_result


def terminal(args: dict, task_id: str = "default") -> str:
    """Execute a shell command."""
    command = args.get("command", "")
    
    if not command.strip():
        return tool_error("Command is empty")
    
    try:
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        output = {
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }
        
        return tool_result(output)
    
    except subprocess.TimeoutExpired:
        return tool_error("Command timed out")
    except Exception as e:
        return tool_error(str(e))


TERMINAL_SCHEMA = {
    "description": "Execute a shell command",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
        },
        "required": ["command"],
    },
}


registry.register(
    name="terminal",
    toolset="terminal",
    schema=TERMINAL_SCHEMA,
    handler=terminal,
    description="Execute shell commands",
    emoji="💻",
)