from flask import Flask, jsonify
import time
import random
from prometheus_client import Counter, Histogram, Gauge, generate_latest

app = Flask(__name__)

# Définition des métriques Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total des requêtes', ['endpoint', 'status'])
LATENCY = Histogram('http_request_duration_seconds', 'Durée des requêtes', ['endpoint'])
ERROR_RATE = Counter('http_errors_total', 'Total des erreurs HTTP', ['endpoint'])
CPU_USAGE = Gauge('cpu_usage', 'Utilisation du CPU (%)')
DB_CNX = Gauge('database_connexions', 'Nbre de connexions simultanées')

@app.route('/fast')
def fast():
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/fast', status='200').inc()
    LATENCY.labels(endpoint='/fast').observe(time.time() - start_time)
    return jsonify({'message': 'Réponse rapide'})

@app.route('/slow')
def slow():
    start_time = time.time()
    time.sleep(random.uniform(1, 3))  # Simulation de latence
    REQUEST_COUNT.labels(endpoint='/slow', status='200').inc()
    LATENCY.labels(endpoint='/slow').observe(time.time() - start_time)
    return jsonify({'message': 'Réponse lente'})

@app.route('/error')
def error():
    REQUEST_COUNT.labels(endpoint='/error', status='500').inc()
    ERROR_RATE.labels(endpoint='/error').inc()
    return jsonify({'message': 'Erreur simulée'}), 500

@app.route('/errorfast')
def errorfast():
    REQUEST_COUNT.labels(endpoint='/errorfast', status='500').inc()
    ERROR_RATE.labels(endpoint='/errorfast').inc()
    LATENCY.labels(endpoint='/errorfast').observe(0.01)
    return jsonify({'message': 'Erreur simulée fast'}), 500

@app.route('/metrics')
def metrics():
    CPU_USAGE.set(random.uniform(10, 90))  # Simulation d'utilisation CPU
    DB_CNX.set(random.uniform(20, 50))  # Simulation de nbre de connexions utilisées
    return generate_latest()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
