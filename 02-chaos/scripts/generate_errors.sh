#!/bin/bash
# Floods /api/error at ~2 req/s for 120 seconds.
# Purpose: trigger the HighErrorRate alert (threshold: rate > 0.7 req/s for 1 minute).
# Watch progress at: http://localhost:9090/alerts

DURATION=120
RATE=2          # requests per second
INTERVAL=0.5    # seconds between requests (1/RATE)
URL="http://localhost:5001/api/error"
COUNT=$((DURATION * RATE))

echo "=== Chaos Experiment 2: Error Rate Flood ==="
echo "Target : $URL"
echo "Rate   : 2 req/s"
echo "Duration: ${DURATION}s (${COUNT} requests)"
echo "Watch  : http://localhost:9090/alerts"
echo ""
echo "Starting in 3 seconds... (Ctrl+C to stop)"
sleep 3

for i in $(seq 1 $COUNT); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
  echo "[$(date +%H:%M:%S)] Request $i/$COUNT → HTTP $STATUS"
  sleep $INTERVAL
done

echo ""
echo "=== Done. Wait ~60s for alert to resolve. ==="
