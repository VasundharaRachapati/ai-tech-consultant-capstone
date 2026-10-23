#!/usr/bin/env bash
# One-command setup + demo for beginners:  ./run.sh   (add --test to run the tests first)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
python run_demo.py "$@"
