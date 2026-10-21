#!/usr/bin/env bash
set -euo pipefail
command -v python3 >/dev/null || { echo 'python3 is required' >&2; exit 1; }
command -v node >/dev/null || { echo 'Node.js 18+ is required' >&2; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<18) process.exit(1)' || { echo 'Node.js 18+ is required' >&2; exit 1; }
DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/python" -m pip install --upgrade pip Pillow
"$DIR/.venv/bin/python" -c 'from PIL import ImageFont'
npx --yes playwright install chromium
