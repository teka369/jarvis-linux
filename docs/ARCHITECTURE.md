# Arquitectura Jarvis Linux

```
USER → INPUT (hotkey/wake) → STT
     → CONTEXT + MEMORY
     → LLM (provider fallback)
     → TOOL REGISTRY
     → PERMISSIONS
     → EXECUTION
     → RESULT → LLM → TTS → USER
```

## Capas

| Capa | Módulo | Responsabilidad |
|---|---|---|
| Config | `jarvis/config.py` | YAML + `.env` secretos |
| Audio | `jarvis/audio/` | micro + TTS |
| Providers | `jarvis/providers/` | STT / LLM / visión multimodal |
| Vision | `jarvis/vision/` | descubrimiento y captura de frames |
| Tools | `jarvis/tools/` | registry + builtins |
| Permissions | `jarvis/core/permissions.py` | READ/WRITE/EXECUTE/CAMERA/DESTRUCTIVE |
| Memory | `jarvis/core/memory.py` | hechos de largo plazo |
| Logs | `jarvis/core/log.py` | INPUT, TOOL_CALL, PERMISSION, RESULT |
| Orchestrator | `jarvis/agent.py` | encadena tools y confirma |

## Visión

1. `list_cameras()` — acceso al dispositivo
2. `capture_frame()` — adquisición
3. `describe_image()` — modelo multimodal
4. `agent.reply()` — razonamiento

Si falla el paso 2, Jarvis **no** afirma que te vio.

## Permisos

`DESTRUCTIVE` pide confirmación hablada (`sí`, `adelante`, `hazlo`).
`CAMERA` se puede apagar en `config.yaml`.
