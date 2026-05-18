"""Terminal Tool Module - Execute shell commands with security checks."""

import subprocess
import json
import logging

from .registry import registry, tool_error, tool_result

logger = logging.getLogger(__name__)


_ALLOW_NETWORK = False
_ALLOW_CODE_EXEC = False
_ALLOW_GIT_WRITE = False


def set_security_settings(
    allow_network: bool = False,
    allow_code_exec: bool = False,
    allow_git_write: bool = False,
):
    """Configure security settings for terminal tool."""
    global _ALLOW_NETWORK, _ALLOW_CODE_EXEC, _ALLOW_GIT_WRITE
    _ALLOW_NETWORK = allow_network
    _ALLOW_CODE_EXEC = allow_code_exec
    _ALLOW_GIT_WRITE = allow_git_write
    logger.info(
        f"Security settings updated: network={allow_network}, "
        f"code_exec={allow_code_exec}, git_write={allow_git_write}"
    )


def get_security_settings() -> dict:
    """Get current security settings."""
    return {
        "allow_network": _ALLOW_NETWORK,
        "allow_code_exec": _ALLOW_CODE_EXEC,
        "allow_git_write": _ALLOW_GIT_WRITE,
    }


def terminal(args: dict, task_id: str = "default") -> str:
    """Execute a shell command with security checks."""
    command = args.get("command", "")
    
    if not command.strip():
        return tool_error("Command is empty")
    
    from agent.security import check_command_safety, get_security_level
    
    is_safe, reason = check_command_safety(
        command,
        allow_network=_ALLOW_NETWORK,
        allow_code_exec=_ALLOW_CODE_EXEC,
        allow_git_write=_ALLOW_GIT_WRITE,
    )
    
    if not is_safe:
        level = get_security_level(command)
        logger.warning(
            f"Security check failed for command '{command}': {reason} "
            f"(level: {level})"
        )
        return tool_error(f"Security check failed: {reason}")
    
    try:
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