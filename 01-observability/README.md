# SRE Lab Phase 1: Observability

This phase covers the fundamentals of observability with a practical hands-on setup using **Prometheus**, **Grafana**, and a **Flask application** that exposes metrics.

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Docker Network: observability           │
├──────────────┬──────────────────┬───────────────┤
│  Flask App   │   Prometheus     │    Grafana    │
│  :5000       │   :9090          │    :3000      │
│  /metrics    │   Time Series DB │  Dashboard    │
└──────────────┴──────────────────┴───────────────┘
```

## Folder Structure

```
01-observability/
├── app/                          # Python Flask Application
│   ├── app.py                    # Flask app with Prometheus metrics
│   ├── Dockerfile                # Docker image definition
│   └── requirements.txt           # Python dependencies
├── prometheus/
│   └── config/
│       └── prometheus.yml         # Prometheus scrape configuration
├── grafana/
│   ├── dashboards/               # Grafana dashboard definitions (JSON)
│   └── provisioning/             # Grafana data sources & dashboards config
└── docker-compose.yml             # Multi-container orchestration
```

## Quick Start

### 1. Build and Start the Stack

```bash
cd 01-observability
docker-compose up --build
```

### 2. Access Services

- **Flask App**: http://localhost:5000
- **Flask Metrics**: http://localhost:5000/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000

### 3. Generate Some Traffic

```bash
# In another terminal
for i in {1..10}; do curl http://localhost:5000/api/data; sleep 1; done
```

### 4. View Metrics in Prometheus

1. Go to http://localhost:9090
2. In the query box, enter: `app_requests_total`
3. Click "Execute" to see metrics

### 5. Set Up Grafana

1. Go to http://localhost:3000
2. Login with `admin` / `admin`
3. Add Prometheus as a data source:
   - URL: `http://prometheus:9090`
   - Click "Save & Test"

## Key Concepts

### Prometheus
- **Time Series Database**: Stores metrics as time series data
- **Scraping**: Pulls metrics from targets at intervals
- **PromQL**: Query language for Prometheus

### Grafana
- **Visualization**: Creates dashboards from metrics
- **Alerting**: Sends alerts based on metric thresholds
- **Provisioning**: Automated setup via config files

### Flask Metrics (Prometheus Client)
- **Counters**: Track total requests
- **Histograms**: Measure request duration
- **Gauges**: Current values (not implemented here)

## Next Steps

- [ ] Create a custom Grafana dashboard
- [ ] Configure alert rules in Prometheus
- [ ] Add more metrics to the Flask app (errors, database queries, etc.)
- [ ] Implement log aggregation with Loki

## Useful PromQL Queries

```promql
# Request rate (requests per second)
rate(app_requests_total[5m])

# 95th percentile request duration
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))

# Current request count
app_requests_total
```

## Stopping the Stack

```bash
docker-compose down
```

To also remove data volumes:
```bash
docker-compose down -v
```

## Troubleshooting

### Prometheus can't reach the app
- Ensure all containers are on the same network: `docker network ls`
- Check container names in prometheus.yml match docker-compose service names

### Grafana won't start
- Check logs: `docker logs sre-lab-grafana`
- Ensure port 3000 is not already in use

### Flask app not exposing metrics
- Verify `/metrics` endpoint works: `curl http://localhost:5000/metrics`
- Check Flask container logs: `docker logs sre-lab-app`
