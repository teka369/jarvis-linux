from .registry import ToolRegistry
from .builtins import all_tools

_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry.register_all(all_tools())
    return _registry


def execute_tool(name: str, arguments: dict, settings) -> str:
    return get_registry().execute(name, arguments, settings)
