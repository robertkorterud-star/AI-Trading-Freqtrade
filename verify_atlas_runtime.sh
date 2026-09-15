#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

printf '\n=== ATLAS: sync and verify ===\n'
printf 'Repository: %s\n' "$REPO_DIR"
printf 'Branch:     feature/ask-atlas\n\n'

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree is not clean."
  echo "Commit/stash local changes before running this verification script."
  exit 1
fi

git fetch origin feature/ask-atlas

git checkout feature/ask-atlas
git reset --hard origin/feature/ask-atlas

git clean -fd

printf '\n=== Baseline ===\n'
git log -3 --oneline

git status --short --branch

printf '\n=== Verify dashboard login template guard ===\n'
grep -n -A2 -B2 'set dashboard = dashboard | default' atlas/dashboard/templates/components/status_bar.html

printf '\n=== Targeted runtime/research tests ===\n'
pytest -q \
  tests/test_runtime_loop.py \
  tests/test_runtime_scheduler_integration.py \
  tests/test_candidate_research_scheduler.py \
  tests/test_candidate_research_service.py \
  tests/test_market_state_trigger.py \
  tests/test_engine_candidate_research.py

printf '\n=== Full pytest suite ===\n'
pytest -q

printf '\n=== Final git status ===\n'
git status --short --branch

git diff --check

printf '\n=== Final commit ===\n'
git log -1 --oneline

printf '\nATLAS runtime verification completed successfully.\n'
