from flask import Flask, jsonify, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

app = Flask(__name__)

# Prometheus metrics
request_count = Counter('app_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('app_request_duration_seconds', 'Request duration', ['endpoint'])

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/api/data', methods=['GET'])
def get_data():
    """Sample API endpoint"""
    request_count.labels(method='GET', endpoint='/api/data').inc()
    
    with request_duration.labels(endpoint='/api/data').time():
        time.sleep(0.1)  # Simulate some work
        return jsonify({
            "status": "success",
            "data": {
                "message": "Hello from SRE Lab Phase 1",
                "timestamp": time.time()
            }
        }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
