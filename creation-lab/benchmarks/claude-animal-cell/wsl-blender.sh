#!/usr/bin/env bash
# Optional host adapter: run a Windows blender.exe from WSL Python.
# Converts absolute Linux path arguments to Windows paths (wslpath -w) and
# forwards the runner's environment controls through WSLENV. It does not
# change Blender arguments, render settings or files. Other hosts pass their
# native Blender to iterate.py directly.
set -euo pipefail
: "${GG3D_WINDOWS_BLENDER:?Set GG3D_WINDOWS_BLENDER to the WSL path of blender.exe}"
args=()
for arg in "$@"; do
  if [[ "$arg" == /* && -e "$arg" ]]; then args+=("$(wslpath -w "$arg")"); else args+=("$arg"); fi
done
export WSLENV="${WSLENV:+$WSLENV:}CUDA_VISIBLE_DEVICES:OMP_NUM_THREADS:PYTHONDONTWRITEBYTECODE"
exec "$GG3D_WINDOWS_BLENDER" "${args[@]}"
