#!/bin/bash
# Continuously hits /api/slow (6s response time) to push p95 latency above the 5s threshold.
# Purpose: trigger the HighLatency alert (threshold: p95 > 5s for 2 minutes).
# Watch progress at: http://localhost:9090/alerts
#
# Run time: at least 3 minutes to confirm alert fires and then resolves.
# Stop with Ctrl+C.

URL="http://localhost:5001/api/slow"

echo "=== Chaos Experiment 3: Latency Spike ==="
echo "Target  : $URL"
echo "Behavior: each request takes ~6 seconds (threshold is 5s p95)"
echo "Watch   : http://localhost:9090/alerts"
echo ""
echo "Starting in 3 seconds... (Ctrl+C to stop)"
sleep 3

REQUEST=0
while true; do
  REQUEST=$((REQUEST + 1))
  curl -s -o /dev/null "$URL" &
  echo "[$(date +%H:%M:%S)] Sent request $REQUEST (running in background, ~6s each)"
  sleep 1
done
