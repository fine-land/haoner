"""Central registry for all agent tools.

This implements the core tool registration mechanism inspired by Hermes.
Each tool file calls `registry.register()` at module level to declare its
schema, handler, and metadata.
"""

import json
import logging
import threading
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn",
        "requires_env", "is_async", "description", "emoji",
    )

    def __init__(self, name, toolset, schema, handler, check_fn=None,
                 requires_env=None, is_async=False, description="", emoji=""):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.requires_env = requires_env or []
        self.is_async = is_async
        self.description = description or schema.get("description", "")
        self.emoji = emoji


class ToolRegistry:
    """Singleton registry that collects tool schemas + handlers from tool files."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._lock = threading.RLock()
        self._generation: int = 0

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable = None,
        requires_env: list = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
    ):
        """Register a tool."""
        with self._lock:
            existing = self._tools.get(name)
            if existing and existing.toolset != toolset:
                logger.error(
                    "Tool registration REJECTED: '%s' (toolset '%s') would "
                    "shadow existing tool from toolset '%s'",
                    name, toolset, existing.toolset,
                )
                return
            self._tools[name] = ToolEntry(
                name=name,
                toolset=toolset,
                schema=schema,
                handler=handler,
                check_fn=check_fn,
                requires_env=requires_env,
                is_async=is_async,
                description=description,
                emoji=emoji,
            )
            self._generation += 1
            logger.debug("Registered tool: %s", name)

    def deregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        with self._lock:
            entry = self._tools.pop(name, None)
            if entry:
                self._generation += 1
                logger.debug("Deregistered tool: %s", name)

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """Return a registered tool entry by name, or None."""
        with self._lock:
            return self._tools.get(name)

    def get_definitions(self, tool_names: Set[str]) -> List[dict]:
        """Return OpenAI-format tool schemas for the requested tool names."""
        result = []
        with self._lock:
            for name in sorted(tool_names):
                entry = self._tools.get(name)
                if not entry:
                    continue
                if entry.check_fn and not entry.check_fn():
                    logger.debug("Tool %s unavailable (check failed)", name)
                    continue
                schema_with_name = {**entry.schema, "name": entry.name}
                result.append({"type": "function", "function": schema_with_name})
        return result

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool handler by name."""
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            if entry.is_async:
                import asyncio
                return asyncio.run(entry.handler(args, **kwargs))
            return entry.handler(args, **kwargs)
        except Exception as e:
            logger.exception("Tool %s dispatch error: %s", name, e)
            return json.dumps({"error": f"Tool execution failed: {type(e).__name__}: {e}"})

    def get_all_tool_names(self) -> List[str]:
        """Return sorted list of all registered tool names."""
        with self._lock:
            return sorted(self._tools.keys())

    def get_toolset_for_tool(self, name: str) -> Optional[str]:
        """Return the toolset a tool belongs to, or None."""
        entry = self.get_entry(name)
        return entry.toolset if entry else None

    def get_schema(self, name: str) -> Optional[dict]:
        """Return the schema for a tool, or None."""
        entry = self.get_entry(name)
        return entry.schema if entry else None


registry = ToolRegistry()


def tool_error(message, **extra) -> str:
    """Return a JSON error string for tool handlers."""
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data=None, **kwargs) -> str:
    """Return a JSON result string for tool handlers."""
    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return json.dumps(kwargs, ensure_ascii=False)