from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Capability(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    CAMERA = "CAMERA"
    MICROPHONE = "MICROPHONE"
    SYSTEM = "SYSTEM"
    DESTRUCTIVE = "DESTRUCTIVE"


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    needs_confirmation: bool
    reason: str


def evaluate(
    capabilities: list[Capability],
    *,
    camera_enabled: bool,
    allow_shell: bool,
    confirmed: bool,
    auto_confirm: list[str],
) -> PermissionDecision:
    names = [c.value for c in capabilities]
    if Capability.CAMERA in capabilities and not camera_enabled:
        return PermissionDecision(False, False, "La cámara está desactivada en config.yaml")
    if Capability.EXECUTE in capabilities and not allow_shell:
        return PermissionDecision(False, False, "EXECUTE está desactivado")
    if Capability.DESTRUCTIVE in capabilities and not confirmed:
        if Capability.DESTRUCTIVE.value in auto_confirm:
            return PermissionDecision(True, False, "auto-confirm DESTRUCTIVE")
        return PermissionDecision(
            False,
            True,
            "Operación destructiva. Confirma explícitamente: 'sí, elimínalo'.",
        )
    if Capability.WRITE in capabilities and "delete" in names:
        if not confirmed:
            return PermissionDecision(False, True, "Escritura destructiva requiere confirmación")
    return PermissionDecision(True, False, "ok")
