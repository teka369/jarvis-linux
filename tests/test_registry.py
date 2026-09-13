from jarvis.tools import get_registry


def test_registry_has_core_tools():
    names = {t.name for t in get_registry()._tools.values()}
    for required in ("open_url", "open_app", "look_camera", "camera_status", "remember"):
        assert required in names


def test_unknown_tool_message():
    from jarvis.config import Settings

    result = get_registry().execute("no_existe", {}, Settings())
    assert "desconocida" in result
