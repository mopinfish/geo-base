#!/bin/bash
# Playwright が test-results/ に書き出す retry-N ディレクトリ数から flaky 件数を集計し、
# GitHub Actions の Job Summary に書き込む。
set -euo pipefail

SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stderr}"

echo "## Flaky tests summary" >> "$SUMMARY"

RESULTS_DIR="app/test-results"
if [ ! -d "$RESULTS_DIR" ]; then
  echo "No test-results directory at $RESULTS_DIR" >> "$SUMMARY"
  exit 0
fi

# 命名規則: <test-id>-retry1, <test-id>-retry2, ...
flaky_count=$(find "$RESULTS_DIR" -type d -name '*-retry*' | wc -l | tr -d ' ')
echo "Retry attempts (= flaky pass + final fail): $flaky_count" >> "$SUMMARY"

if [ "$flaky_count" -gt 0 ]; then
  echo "" >> "$SUMMARY"
  echo "Affected tests:" >> "$SUMMARY"
  find "$RESULTS_DIR" -type d -name '*-retry*' -print | sed 's|^|- |' >> "$SUMMARY"
fi
