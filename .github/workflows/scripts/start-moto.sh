#!/bin/bash
# moto S3 を localhost:5000 で起動する。CI 用バックグラウンドプロセス（Issue #112 TS-12）。
#
# 起動後 `MOTO_PID` を `$GITHUB_ENV` に書き出すので、ワークフロー側の
# "Stop background servers" ステップで `kill "$MOTO_PID"` できる。
# API (boto3) は `S3_ENDPOINT_URL=http://localhost:5000` 経由でここに向かう。
set -euo pipefail

# api ディレクトリで `uv run` するのは pyproject.toml の dev extra (moto[s3]) を
# 解決した venv を使うため。e2e-setup composite action が `uv sync --extra dev`
# 済みなのを前提とする。
cd "$(dirname "$0")/../../.."  # repo root
cd api

nohup uv run python -m moto.server -p 5000 > /tmp/moto.log 2>&1 &
MOTO_PID=$!
echo "MOTO_PID=$MOTO_PID" >> "${GITHUB_ENV:-/dev/null}"

# 起動待ち (最大 10 秒)。moto のヘルスチェック相当は `/moto-api/` が 200 を返すこと。
for i in $(seq 1 20); do
  if curl -fsS http://localhost:5000/moto-api/ > /dev/null 2>&1; then
    echo "moto ready (pid=$MOTO_PID)"
    exit 0
  fi
  sleep 0.5
done

echo "moto failed to start within 10s" >&2
echo "--- /tmp/moto.log ---" >&2
cat /tmp/moto.log >&2 || true
exit 1
