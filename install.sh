#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.local/share/jarvis-linux/venv"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/jarvis-linux"

echo "==> Instalando Jarvis en $VENV"
mkdir -p "$VENV" "$BIN" "$CFG" "$HOME/.local/share/applications"

python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$ROOT/requirements.txt"

cat > "$BIN/jarvis" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" -m jarvis "\$@"
EOF
chmod +x "$BIN/jarvis"

# Hace importable el paquete
SITE="$("$VENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
echo "$ROOT" > "$SITE/jarvis-linux.pth"

if [[ ! -f "$CFG/.env" ]]; then
  cp "$ROOT/.env.example" "$CFG/.env"
fi
if [[ ! -f "$CFG/config.yaml" ]]; then
  cp "$ROOT/config.example.yaml" "$CFG/config.yaml"
fi
# El loader también lee el .env del repo; enlazamos uno cómodo
if [[ ! -f "$ROOT/.env" ]]; then
  ln -s "$CFG/.env" "$ROOT/.env" || cp "$CFG/.env" "$ROOT/.env"
fi
if [[ ! -f "$ROOT/config.yaml" ]]; then
  ln -s "$CFG/config.yaml" "$ROOT/config.yaml" || true
fi

cp "$ROOT/packaging/jarvis.desktop" "$HOME/.local/share/applications/jarvis.desktop"
sed -i "s|^Exec=.*|Exec=$BIN/jarvis once|" "$HOME/.local/share/applications/jarvis.desktop" || true

mkdir -p "$HOME/.config/systemd/user"
cp "$ROOT/systemd/jarvis.service" "$HOME/.config/systemd/user/jarvis.service"
systemctl --user daemon-reload || true

echo
echo "Listo."
echo "1. Edita tus llaves:  nano $CFG/.env"
echo "2. Prueba:            jarvis doctor"
echo "3. Un comando:        jarvis once"
echo "4. Texto:             jarvis text abre firefox"
echo "5. Siempre atento:    systemctl --user enable --now jarvis.service"
echo
echo "En KDE: Preferencias del sistema → Atajos → comando personalizado"
echo "Comando: $BIN/jarvis once"
echo "Atajo sugerido: Meta+J"
echo
echo "Voz por defecto: es-CO-GonzaloNeural (cámbiala en $CFG/config.yaml)"
