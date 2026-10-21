#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
command -v node >/dev/null || { echo '{"ok":false,"error":"Node 18+ missing"}'; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<18) process.exit(1)' || { echo '{"ok":false,"error":"Node 18+ required"}'; exit 1; }
test -x "$DIR/.venv/bin/python" || { echo '{"ok":false,"error":"run scripts/setup.sh first"}'; exit 1; }
"$DIR/.venv/bin/python" "$(dirname "$0")/build.py" "$1" "$2"
