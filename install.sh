#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/.local/share/jarvis-linux/venv"
BIN="$HOME/.local/bin"
CFG="$HOME/.config/jarvis-linux"

echo "==> Instalando Jarvis en $VENV"
mkdir -p "$VENV" "$BIN" "$CFG" "$HOME/.local/share/applications"

python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$ROOT/requirements.txt"

SITE="$("$VENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')"
for d in /usr/lib/python3*/site-packages /usr/lib64/python3*/site-packages; do
  if [[ -d "$d/PySide6" ]]; then
    echo "$d" > "$SITE/system-qt.pth"
  fi
done

cat > "$BIN/jarvis" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/python" -m jarvis "\$@"
EOF
chmod +x "$BIN/jarvis"

echo "$ROOT" > "$SITE/jarvis-linux.pth"

if [[ ! -f "$CFG/.env" ]]; then
  cp "$ROOT/.env.example" "$CFG/.env"
fi
if [[ ! -f "$CFG/config.yaml" ]]; then
  cp "$ROOT/config.example.yaml" "$CFG/config.yaml"
fi
if [[ ! -f "$ROOT/.env" ]]; then
  ln -s "$CFG/.env" "$ROOT/.env" || cp "$CFG/.env" "$ROOT/.env"
fi
if [[ ! -f "$ROOT/config.yaml" ]]; then
  ln -s "$CFG/config.yaml" "$ROOT/config.yaml" || true
fi

cp "$ROOT/packaging/jarvis.desktop" "$HOME/.local/share/applications/jarvis.desktop"
sed -i "s|^Exec=.*|Exec=$BIN/jarvis ui|" "$HOME/.local/share/applications/jarvis.desktop" || true

mkdir -p "$HOME/.config/systemd/user"
cp "$ROOT/systemd/jarvis.service" "$HOME/.config/systemd/user/jarvis.service"
cp "$ROOT/systemd/jarvis-ui.service" "$HOME/.config/systemd/user/jarvis-ui.service"
systemctl --user daemon-reload || true

echo
echo "Listo."
echo "Avatar:              jarvis ui"
echo "Atajo KDE:           $BIN/jarvis trigger   (Meta+Shift+J)"
echo "Autostart UI:        systemctl --user enable --now jarvis-ui.service"
