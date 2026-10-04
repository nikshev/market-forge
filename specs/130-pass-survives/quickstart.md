# Quickstart

1. `.venv/bin/python -m pytest tests/unit/pipeline/test_passes.py -q`
2. Live: `docker compose run --rm --no-deps -e CHANNELFLOW_S3_ENDPOINT=http://127.0.0.1:1 worker` (with a short
   interval) — it keeps running and prints `pass failed` each interval, where before it exited at the first.
