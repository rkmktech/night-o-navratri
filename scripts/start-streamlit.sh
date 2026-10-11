#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

node scripts/sync-dance-guides.mjs

# Use the same port for the managed web service and published application.
export PORT=8080
export STREAMLIT_SERVER_PORT=8080
exec python -m streamlit run streamlit_app/app.py \
  --server.port 8080 \
  --server.address 0.0.0.0
