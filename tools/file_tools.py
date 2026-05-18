"""File Tools Module - LLM agent file manipulation tools."""

import json
import os
from pathlib import Path

from .registry import registry, tool_error, tool_result


def read_file(args: dict, task_id: str = "default") -> str:
    """Read a file with pagination."""
    path = args.get("path", "")
    offset = args.get("offset", 1)
    limit = args.get("limit", 500)

    try:
        p = Path(path).expanduser().resolve()
        
        # Security check: block device files
        blocked_paths = {"/dev/zero", "/dev/random", "/dev/urandom", "/dev/stdin", "/dev/stdout", "/dev/stderr"}
        if str(p) in blocked_paths:
            return tool_error(f"Cannot read device file: {path}")
        
        # Check if file exists
        if not p.exists():
            return tool_error(f"File not found: {path}")
        
        # Check if it's a file
        if not p.is_file():
            return tool_error(f"Not a file: {path}")
        
        # Read file
        with open(p, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        offset = max(1, offset)
        limit = max(1, limit)
        
        start_idx = offset - 1
        end_idx = start_idx + limit
        
        selected_lines = lines[start_idx:end_idx]
        content = ''.join(selected_lines)
        
        result = {
            "content": content,
            "path": str(p),
            "offset": offset,
            "limit": limit,
            "total_lines": total_lines,
            "truncated": end_idx < total_lines,
        }
        
        return tool_result(result)
    
    except Exception as e:
        return tool_error(str(e))


def write_file(args: dict, task_id: str = "default") -> str:
    """Write content to a file."""
    path = args.get("path", "")
    content = args.get("content", "")

    try:
        p = Path(path).expanduser().resolve()
        
        # Security check: prevent writing to sensitive paths
        sensitive_prefixes = ("/etc/", "/boot/", "/usr/lib/systemd/")
        if any(str(p).startswith(prefix) for prefix in sensitive_prefixes):
            return tool_error(f"Refusing to write to sensitive system path: {path}")
        
        # Create parent directories if needed
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(p, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return tool_result(
            success=True,
            path=str(p),
            message=f"File written successfully: {path}"
        )
    
    except Exception as e:
        return tool_error(str(e))


# Tool schemas
READ_FILE_SCHEMA = {
    "description": "Read a file with pagination support",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "offset": {"type": "integer", "description": "Starting line number (default: 1)", "minimum": 1},
            "limit": {"type": "integer", "description": "Number of lines to read (default: 500)", "minimum": 1},
        },
        "required": ["path"],
    },
}

WRITE_FILE_SCHEMA = {
    "description": "Write content to a file",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
}


registry.register(
    name="read_file",
    toolset="file_tools",
    schema=READ_FILE_SCHEMA,
    handler=read_file,
    description="Read a file with pagination",
    emoji="📄",
)

registry.register(
    name="write_file",
    toolset="file_tools",
    schema=WRITE_FILE_SCHEMA,
    handler=write_file,
    description="Write content to a file",
    emoji="✍️",
)