#!/bin/bash
# Playwright が test-results/ に書き出す retry-N ディレクトリ数から flaky 件数を集計し、
# GitHub Actions の Job Summary に書き込む。Phase 3 拡張: 総テスト数で割って
# flake 率も出すことで、目標値 (< 2%) との比較がしやすくなる。
set -euo pipefail

SUMMARY="${GITHUB_STEP_SUMMARY:-/dev/stderr}"

echo "## Flaky tests summary" >> "$SUMMARY"

RESULTS_DIR="app/test-results"
if [ ! -d "$RESULTS_DIR" ]; then
  echo "No test-results directory at $RESULTS_DIR" >> "$SUMMARY"
  exit 0
fi

flaky_count=$(find "$RESULTS_DIR" -type d -name '*-retry*' | wc -l | tr -d ' ')
total_count=$(find "$RESULTS_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')

echo "Total test attempts: $total_count" >> "$SUMMARY"
echo "Retry attempts (= flaky pass + final fail): $flaky_count" >> "$SUMMARY"

if [ "$total_count" -gt 0 ] && [ "$flaky_count" -gt 0 ]; then
  rate=$(echo "scale=2; $flaky_count * 100 / $total_count" | bc 2>/dev/null || echo "?")
  echo "Approximate flake rate: ${rate}% (target: < 2%)" >> "$SUMMARY"
fi

if [ "$flaky_count" -gt 0 ]; then
  echo "" >> "$SUMMARY"
  echo "Affected tests:" >> "$SUMMARY"
  find "$RESULTS_DIR" -type d -name '*-retry*' -print | sed 's|^|- |' >> "$SUMMARY"
fi
