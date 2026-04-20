#!/bin/bash
# Activates venv and runs the 24h script
# Usage: ./run_24h.sh

set -e
cd /home/anon/Projects/experiment/MoneyPrinterV2
source venv/bin/activate 2>/dev/null || true
exec python3 scripts/run_24h.py >> logs/run_24h_stdout.log 2>> logs/run_24h_stderr.log
