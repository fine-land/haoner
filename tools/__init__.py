"""Tools module initialization.

Imports all tool modules to ensure they register themselves with the registry.
"""

# Import all tool modules to trigger registration
from . import file_tools
from . import terminal_tool

# Re-export commonly used items
from .registry import registry, tool_error, tool_result
from .model_tools import get_tool_definitions, handle_function_call, coerce_tool_args
