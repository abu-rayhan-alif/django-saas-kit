#!/usr/bin/env bash
# Install dev/test requirements with pinned typing stubs (CI + local).
set -euo pipefail

cd "$(dirname "$0")/.."

python scripts/verify_requirements_pins.py

python -m pip install --upgrade pip
python -m pip install -r requirements/typing-stubs.txt
python -m pip install -r requirements/local.txt -c requirements/constraints.txt
