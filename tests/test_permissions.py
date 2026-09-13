from jarvis.core.permissions import Capability, evaluate


def test_camera_disabled_blocks():
    decision = evaluate(
        [Capability.CAMERA],
        camera_enabled=False,
        allow_shell=True,
        confirmed=False,
        auto_confirm=[],
    )
    assert decision.allowed is False
    assert "cámara" in decision.reason.lower() or "camara" in decision.reason.lower()


def test_destructive_needs_confirmation():
    decision = evaluate(
        [Capability.DESTRUCTIVE, Capability.WRITE],
        camera_enabled=True,
        allow_shell=True,
        confirmed=False,
        auto_confirm=[],
    )
    assert decision.needs_confirmation is True
    assert decision.allowed is False


def test_destructive_confirmed():
    decision = evaluate(
        [Capability.DESTRUCTIVE],
        camera_enabled=True,
        allow_shell=True,
        confirmed=True,
        auto_confirm=[],
    )
    assert decision.allowed is True


def test_open_app_allowed():
    decision = evaluate(
        [Capability.EXECUTE],
        camera_enabled=True,
        allow_shell=True,
        confirmed=False,
        auto_confirm=[],
    )
    assert decision.allowed is True
