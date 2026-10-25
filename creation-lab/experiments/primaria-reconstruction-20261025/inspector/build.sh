#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash build.sh <absolute-makecode-root>" >&2
  exit 2
fi
ROOT="$(cd "$1" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THREE="$ROOT/cotizador/node_modules/three"
ESBUILD="$ROOT/cotizador/node_modules/@esbuild/linux-x64/bin/esbuild"

[[ -x "$ESBUILD" ]] || { echo "Missing local esbuild binary: $ESBUILD" >&2; exit 1; }
[[ -f "$THREE/package.json" ]] || { echo "Missing local Three.js package: $THREE" >&2; exit 1; }

NODE_PATH="$ROOT/cotizador/node_modules" "$ESBUILD" "$SCRIPT_DIR/viewer.js" \
  --bundle \
  --format=esm \
  --platform=browser \
  --target=es2020 \
  --outfile="$SCRIPT_DIR/viewer.bundle.js"
cp "$THREE/LICENSE" "$SCRIPT_DIR/THREE-LICENSE.txt"

