# J.A.R.V.I.S. para Linux

Asistente de voz para KDE Plasma / Linux. Dices **Jarvis, abre Google** y lo hace.

Tú solo pones las API keys gratis. El resto ya está armado: micrófono, wake word, voz, cámara, captura de pantalla y control del escritorio.

## Qué hace

- Escucha **Jarvis** (o pulsas `Meta+J`)
- Transcribe con **Groq Whisper** (respaldo Gemini)
- Razona con **Gemini Flash** (respaldo Groq / NVIDIA / OpenRouter)
- Habla con **Edge TTS**, voz colombiana `es-CO-GonzaloNeural` — sin API key
- Abre Firefox, URLs, Kate, Konsole, archivos
- Mira la webcam o la pantalla cuando se lo pides
- Lista blanca de comandos para no disparar `rm -rf` por accidente

## Lo que tienes que hacer tú

1. Crear un repo vacío en GitHub llamado `jarvis-linux` (si quieres versionarlo ahí) **o** clonar esta carpeta.
2. Sacar llaves gratis:
   - [Groq](https://console.groq.com/keys) — voz rápida
   - [Google AI Studio](https://aistudio.google.com/app/apikey) — cerebro + cámara
3. Instalar y pegar las llaves.

NVIDIA NIM y OpenRouter son opcionales.

## Instalación

```bash
sudo apt install python3-venv python3-pip portaudio19-dev ffmpeg \
  pulseaudio-utils libnotify-bin xdg-utils spectacle -y
# Fedora: python3-virtualenv portaudio-devel ffmpeg libnotify xdg-utils spectacle
# Arch:   python-virtualenv portaudio ffmpeg libnotify xdg-utils spectacle

chmod +x install.sh
./install.sh
nano ~/.config/jarvis-linux/.env
jarvis doctor
```

Ejemplo de `.env`:

```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
```

## Uso

```bash
jarvis once              # te escucha una vez (atajo de teclado)
jarvis listen            # queda en segundo plano, espera "Jarvis..."
jarvis text abre firefox
jarvis doctor
```

Atajo en KDE:

1. Preferencias del sistema → Atajos → Añadir comando
2. Comando: `~/.local/bin/jarvis once`
3. Atajo: **Meta+J**

Siempre encendido:

```bash
systemctl --user enable --now jarvis.service
```

El modo `listen` gasta cuota de STT en cada frase que detecta. Para uso diario, `once` + atajo es mejor.

## Ejemplos

- *Jarvis, ¿estás ahí?*
- *Jarvis, abre Google*
- *Jarvis, abre YouTube y busca lofi*
- *Jarvis, abre Konsole*
- *Mírame* / *¿qué hay en la cámara?*
- *¿Qué se ve en la pantalla?*
- *Crea un archivo en Documentos/ideas.md con la lista de mañana*

## Voz

Por defecto usa `es-CO-GonzaloNeural`. Otras buenas:

```yaml
tts:
  voice: es-MX-JorgeNeural     # más grave
  # voice: es-ES-AlvaroNeural
  # voice: en-GB-RyanNeural     # Jarvis en inglés
```

Lista: `edge-tts --list-voices | grep es-`

## Seguridad

`run_command` solo acepta binarios de `safety.allowed_bins` en `config.yaml`.
No escribe fuera de tu `$HOME`.
Patrones tipo `rm -rf`, `mkfs`, `shutdown` están bloqueados.

## Estructura

```
jarvis/
  app.py           bucle de voz
  agent.py         LLM + herramientas
  audio/           micro + TTS
  providers/       Groq / Gemini / NVIDIA / OpenRouter
  tools/           escritorio, cámara, screenshot
```

## Requisitos

- Linux con PipeWire o Pulse
- Python 3.10+
- Micrófono
- Opcional: `/dev/video0` + `ffmpeg` para cámara
- Opcional: `spectacle` (KDE) para capturas

MIT
