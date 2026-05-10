import logging
import time

from flask import Flask, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

# Structured JSON logger
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Prometheus metrics
request_count = Counter('app_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('app_request_duration_seconds', 'Request duration', ['endpoint'])
error_count = Counter('app_errors_total', 'Total errors', ['endpoint', 'status_code'])


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route('/api/data', methods=['GET'])
def get_data():
    request_count.labels(method='GET', endpoint='/api/data').inc()
    start = time.time()

    with request_duration.labels(endpoint='/api/data').time():
        time.sleep(0.1)
        duration = time.time() - start
        logger.info("request", extra={"endpoint": "/api/data", "status": 200, "duration": round(duration, 3)})
        return jsonify({
            "status": "success",
            "data": {
                "message": "Hello from SRE Lab Phase 1",
                "timestamp": time.time()
            }
        }), 200


@app.route('/api/error', methods=['GET'])
def get_error():
    request_count.labels(method='GET', endpoint='/api/error').inc()
    error_count.labels(endpoint='/api/error', status_code='500').inc()
    with request_duration.labels(endpoint='/api/error').time():
        logger.error("request", extra={"endpoint": "/api/error", "status": 500})
        return jsonify({"status": "error", "message": "Simulated failure"}), 500


@app.route('/api/slow', methods=['GET'])
def get_slow():
    request_count.labels(method='GET', endpoint='/api/slow').inc()
    start = time.time()
    with request_duration.labels(endpoint='/api/slow').time():
        time.sleep(6)
    duration = time.time() - start
    logger.info("request", extra={"endpoint": "/api/slow", "status": 200, "duration": round(duration, 3)})
    return jsonify({"status": "success", "message": "Slow response simulated"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
