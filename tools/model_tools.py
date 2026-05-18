"""
Model Tools Module - Thin orchestration layer over the tool registry.

Public API:
    get_tool_definitions(enabled_toolsets, disabled_toolsets) -> list
    handle_function_call(function_name, function_args, task_id) -> str
"""

import json
import logging
from typing import Dict, Any, List, Optional

from .registry import registry

logger = logging.getLogger(__name__)


# Tools whose execution is intercepted by the agent loop
_AGENT_LOOP_TOOLS = {"todo", "memory", "session_search"}


def coerce_tool_args(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce tool call arguments to match their JSON Schema types.
    
    LLMs frequently return numbers as strings ("42" instead of 42)
    and booleans as strings ("true" instead of true).
    """
    if not args or not isinstance(args, dict):
        return args

    schema = registry.get_schema(tool_name)
    if not schema:
        return args

    properties = (schema.get("parameters") or {}).get("properties")
    if not properties:
        return args

    for key, value in list(args.items()):
        prop_schema = properties.get(key)
        if not prop_schema:
            continue
        
        expected = prop_schema.get("type")
        
        if expected == "array" and value is not None and not isinstance(value, (list, tuple)):
            args[key] = [value]
            continue
        
        if not isinstance(value, str):
            continue
        
        if expected == "integer":
            try:
                args[key] = int(value)
            except ValueError:
                pass
        elif expected == "number":
            try:
                args[key] = float(value)
            except ValueError:
                pass
        elif expected == "boolean":
            low = value.lower()
            if low == "true":
                args[key] = True
            elif low == "false":
                args[key] = False
        elif expected == "object" or expected == "array":
            try:
                args[key] = json.loads(value)
            except ValueError:
                pass

    return args


def get_tool_definitions(
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
) -> List[Dict[str, Any]]:
    """Get tool definitions for model API calls with toolset-based filtering."""
    all_tools = registry.get_all_tool_names()
    
    if enabled_toolsets:
        tools_to_include = set()
        for toolset in enabled_toolsets:
            tools_to_include.update([
                name for name in all_tools 
                if registry.get_toolset_for_tool(name) == toolset
            ])
    else:
        tools_to_include = set(all_tools)
    
    if disabled_toolsets:
        for toolset in disabled_toolsets:
            tools_to_include.difference_update([
                name for name in all_tools 
                if registry.get_toolset_for_tool(name) == toolset
            ])
    
    return registry.get_definitions(tools_to_include)


def handle_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    task_id: Optional[str] = None,
    **kwargs
) -> str:
    """Main function call dispatcher that routes calls to the tool registry."""
    function_args = coerce_tool_args(function_name, function_args)
    
    try:
        if function_name in _AGENT_LOOP_TOOLS:
            return json.dumps({"error": f"{function_name} must be handled by the agent loop"})
        
        return registry.dispatch(function_name, function_args, task_id=task_id, **kwargs)
    
    except Exception as e:
        error_msg = f"Error executing {function_name}: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)