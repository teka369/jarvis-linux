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
    from ..core.events import AvatarState, BUS

    visual = {
        "web_search": AvatarState.SEARCHING,
        "open_url": AvatarState.SEARCHING,
        "look_camera": AvatarState.EXECUTING,
        "screenshot": AvatarState.EXECUTING,
        "run_command": AvatarState.EXECUTING,
    }.get(name)
    if visual:
        BUS.set_state(visual)
    return get_registry().execute(name, arguments, settings)
