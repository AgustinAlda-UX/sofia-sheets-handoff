#!/usr/bin/env bash
# Captura headless de una preview a tamaño exacto (1x) para comparar con Figma.
# Uso: tools/shot.sh previews/<group>--<id>.html out.png <width> <height>
# Chrome headless a veces no termina tras escribir el PNG: se lanza en background y se mata al detectar el archivo.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IN="$1"; OUT="$2"; W="$3"; H="$4"
case "$IN" in /*) ;; *) IN="$ROOT/$IN";; esac
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT";; esac
rm -f "$OUT"
PROFILE="$(mktemp -d)"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --user-data-dir="$PROFILE" --no-first-run --no-default-browser-check \
  --virtual-time-budget=5000 --window-size="${W},${H}" \
  --screenshot="$OUT" "file://$IN" >/dev/null 2>&1 &
PID=$!
for i in $(seq 1 60); do
  if [ -s "$OUT" ]; then sleep 0.5; break; fi
  sleep 0.5
done
pkill -P "$PID" 2>/dev/null; kill "$PID" 2>/dev/null; pkill -f "$PROFILE" 2>/dev/null
rm -rf "$PROFILE"
if [ -s "$OUT" ]; then echo "$OUT"; else echo "ERROR: no se generó $OUT" >&2; exit 1; fi
