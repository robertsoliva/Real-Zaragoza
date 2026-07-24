#!/bin/bash
# Start the RZ Analytics local dev server.
# Requires ANTHROPIC_API_KEY in your environment (add to ~/.zshrc).

set -euo pipefail

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "Error: ANTHROPIC_API_KEY is not set."
  echo "Add this to your ~/.zshrc:"
  echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
  echo "Then run: source ~/.zshrc"
  exit 1
fi

export GCP_PROJECT_ID=real-zaragoza-500608

cd "$(dirname "$0")"
echo "Starting RZ Analytics at http://127.0.0.1:5050"
python3 app.py
