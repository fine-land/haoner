"""
Security Module for Haoner Agent

Based on Claude Code's security mechanisms:
- Working directory validation
- Dangerous command detection
- Read-only command whitelist
- Path safety checks
- Command execution validation
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


ALLOWED_WORKING_DIR = os.getcwd()


SAFE_GIT_COMMANDS = {
    "git status": {
        "safe_flags": [
            "--short", "-s", "--branch", "-b", "--porcelain", "--long",
            "--verbose", "-v", "-u", "--ignore-submodules", "--ignored"
        ]
    },
    "git diff": {
        "safe_flags": [
            "--stat", "--numstat", "--name-only", "--name-status", "--color",
            "--no-color", "--cached", "--staged", "-p", "-u", "-M", "-C"
        ]
    },
    "git log": {
        "safe_flags": [
            "--oneline", "--graph", "--decorate", "--max-count", "-n",
            "--since", "--after", "--until", "--before", "--author",
            "--grep", "-p", "--stat"
        ]
    },
    "git show": {
        "safe_flags": [
            "--oneline", "--stat", "--name-only", "--color", "-p"
        ]
    },
    "git branch": {
        "safe_flags": [
            "-a", "-v", "-vv", "--list", "-r", "-l"
        ]
    },
    "git stash list": {
        "safe_flags": []
    },
    "git remote -v": {
        "safe_flags": []
    },
    "git remote show": {
        "safe_flags": ["-n"]
    },
    "git ls-files": {
        "safe_flags": [
            "--cached", "--deleted", "--modified", "--others", "--ignored",
            "--stage", "--directory", "--no-empty-directory"
        ]
    },
    "git rev-parse": {
        "safe_flags": [
            "--verify", "--short", "--abbrev-ref", "--symbolic",
            "--show-toplevel", "--git-dir", "--is-inside-work-tree"
        ]
    },
    "git merge-base": {
        "safe_flags": [
            "--is-ancestor", "--fork-point", "--octopus", "--independent"
        ]
    },
    "git describe": {
        "safe_flags": [
            "--tags", "--match", "--long", "--always", "--dirty"
        ]
    },
    "git cat-file": {
        "safe_flags": ["-t", "-s", "-p", "-e", "--batch-check"]
    },
    "git for-each-ref": {
        "safe_flags": [
            "--format", "--sort", "--count", "--merged", "--no-merged"
        ]
    },
    "git reflog": {
        "safe_flags": [
            "--oneline", "--date", "--all", "--max-count", "-n"
        ]
    },
    "git ls-remote": {
        "safe_flags": [
            "--heads", "--tags", "--refs", "--get-url", "-q"
        ]
    },
}

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r":(){ :|:& };:",
    r"curl\s+.*\|\s*sh",
    r"wget\s+.*\|\s*sh",
    r"eval\s+.*\$",
    r"exec\s+.*\$",
    r"--no-check-certificate",
    r"\\?\s*>\s*/dev/sd[a-z]",
    r"dd\s+.*of=/dev/",
    r"mkfs\s+",
    r"umount\s+",
    r"kill\s+-9\s+1",
    r"chmod\s+-R\s+777",
    r"chown\s+-R\s+root:",
]

CODE_EXECUTION_PATTERNS = [
    r"python\s+.*-c\s+",
    r"python\s+.*eval\(",
    r"node\s+.*-e\s+",
    r"node\s+.*eval\(",
    r"bash\s+.*-c\s+",
    r"sh\s+.*-c\s+",
    r"ruby\s+.*-e\s+",
    r"perl\s+.*-e\s+",
    r"php\s+.*-r\s+",
    r"eval\s+",
    r"exec\s+",
    r"source\s+.*\.sh",
    r"\.\s+.*\.sh",
]

NETWORK_PATTERNS = [
    r"curl\s+",
    r"wget\s+",
    r"nc\s+",
    r"netcat\s+",
    r"ssh\s+",
    r"scp\s+",
    r"rsync\s+",
    r"ftp\s+",
    r"telnet\s+",
]


class SecurityError(Exception):
    """Security check failed exception"""
    def __init__(self, message: str, reason: str):
        super().__init__(message)
        self.reason = reason


def check_working_directory(command: str, cwd: str = None) -> Tuple[bool, str]:
    """
    Check if command tries to change to an unsafe directory.
    
    Returns:
        Tuple of (is_safe, message)
    """
    if cwd is None:
        cwd = ALLOWED_WORKING_DIR
    
    original_cwd = os.getcwd()
    
    cd_pattern = re.match(r'^cd\s+(.+?)(?:\s+&&|\s*\||$)', command)
    if cd_pattern:
        target_dir = cd_pattern.group(1).strip()
        target_dir = os.path.expanduser(target_dir)
        
        if os.path.isabs(target_dir):
            target_path = target_dir
        else:
            target_path = os.path.join(original_cwd, target_dir)
        
        try:
            target_path = os.path.realpath(target_path)
            allowed_path = os.path.realpath(cwd)
            
            if not target_path.startswith(allowed_path):
                return False, f"Directory '{target_dir}' is outside allowed working directory"
        except Exception as e:
            return False, f"Failed to validate directory: {e}"
    
    return True, ""


def check_dangerous_patterns(command: str) -> Tuple[bool, str]:
    """
    Check for dangerous command patterns.
    
    Returns:
        Tuple of (is_safe, reason)
    """
    cmd_lower = command.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return False, f"Dangerous pattern detected: {pattern}"
    
    return True, ""


def check_code_execution(command: str) -> Tuple[bool, str]:
    """
    Check for code execution patterns that could be dangerous.
    
    Returns:
        Tuple of (is_safe, reason)
    """
    for pattern in CODE_EXECUTION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Potentially dangerous code execution: {pattern}"
    
    return True, ""


def check_network_access(command: str) -> Tuple[bool, str]:
    """
    Check for network access commands.
    
    Returns:
        Tuple of (is_safe, reason)
    """
    for pattern in NETWORK_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Network access detected: {pattern}"
    
    return True, ""


def check_git_command_safety(command: str) -> Tuple[bool, str]:
    """
    Validate git commands against whitelist.
    
    Returns:
        Tuple of (is_safe, reason)
    """
    command = command.strip()
    
    for safe_cmd, config in SAFE_GIT_COMMANDS.items():
        if command.startswith(safe_cmd):
            safe_flags = config.get("safe_flags", [])
            if safe_flags:
                return True, ""
            
            remaining = command[len(safe_cmd):].strip()
            if not remaining:
                return True, ""
            
            return True, ""
    
    if command.startswith("git "):
        return False, f"Git command '{command}' is not in the safe list"
    
    return True, ""


def check_path_traversal(command: str) -> Tuple[bool, str]:
    """
    Check for path traversal attempts.
    
    Returns:
        Tuple of (is_safe, reason)
    """
    path_patterns = [
        r"\.\./",
        r"\.\.\\",
        r"/\.\./",
        r"\./\.\./",
        r"(^|[?&|;])\s*\.\./",
        r"(^|[?&|;])\s*\.\.\\",
    ]
    
    for pattern in path_patterns:
        if re.search(pattern, command):
            return False, f"Path traversal detected"
    
    return True, ""


def check_command_safety(
    command: str,
    allow_network: bool = False,
    allow_code_exec: bool = False,
    allow_git_write: bool = False,
    cwd: str = None
) -> Tuple[bool, str]:
    """
    Comprehensive security check for a command.
    
    Args:
        command: The command to check
        allow_network: Whether to allow network access commands
        allow_code_exec: Whether to allow code execution patterns
        allow_git_write: Whether to allow git write commands
        cwd: Allowed working directory (defaults to project root)
    
    Returns:
        Tuple of (is_safe, reason)
    """
    if not command or not command.strip():
        return False, "Empty command"
    
    if not allow_git_write:
        git_write_patterns = [
            r"git\s+push",
            r"git\s+commit\s+-am",
            r"git\s+commit\s+--amend",
            r"git\s+force-push",
            r"git\s+push\s+--force",
            r"git\s+rebase",
            r"git\s+reset\s+--hard",
            r"git\s+checkout\s+-f",
            r"git\s+branch\s+-D",
            r"git\s+branch\s+--delete",
        ]
        for pattern in git_write_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Git write operation not allowed: {pattern}"
    
    is_safe, reason = check_working_directory(command, cwd)
    if not is_safe:
        return False, reason
    
    is_safe, reason = check_dangerous_patterns(command)
    if not is_safe:
        return False, reason
    
    is_safe, reason = check_path_traversal(command)
    if not is_safe:
        return False, reason
    
    if not allow_network:
        is_safe, reason = check_network_access(command)
        if not is_safe:
            return False, reason
    
    if not allow_code_exec:
        is_safe, reason = check_code_execution(command)
        if not is_safe:
            return False, reason
    
    if not allow_git_write:
        is_safe, reason = check_git_command_safety(command)
        if not is_safe:
            return False, reason
    
    return True, ""


def get_security_level(command: str) -> str:
    """
    Determine the security level of a command.
    
    Returns:
        One of: "safe", "elevated", "dangerous", "blocked"
    """
    is_safe, _ = check_command_safety(command)
    if is_safe:
        return "safe"
    
    elevated_patterns = [
        r"sudo\s+",
        r"chmod\s+[0-7][0-7][0-7]",
        r"chown\s+",
        r"kill\s+",
        r"killall\s+",
    ]
    for pattern in elevated_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return "elevated"
    
    dangerous_patterns = [
        r"rm\s+-rf",
        r"dd\s+",
        r"mkfs\s+",
        r"umount\s+",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return "dangerous"
    
    return "blocked"


if __name__ == "__main__":
    test_commands = [
        "ls -la",
        "git status",
        "cd /tmp && ls",
        "cd ../ && ls",
        "curl http://example.com",
        "python -c 'print(1)'",
        "rm -rf /tmp/test",
    ]
    
    for cmd in test_commands:
        is_safe, reason = check_command_safety(cmd)
        level = get_security_level(cmd)
        print(f"Command: {cmd}")
        print(f"  Safe: {is_safe}, Reason: {reason or 'OK'}")
        print(f"  Level: {level}")
        print()
