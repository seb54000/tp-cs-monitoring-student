from flask import Flask, Response, jsonify
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

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')

@app.route('/fast')
def fast():
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/fast', status='200').inc()
    LATENCY.labels(endpoint='/fast').observe(random.uniform(0.001, 0.005))
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    return jsonify({'message': 'Réponse rapide'})

@app.route('/slow')
def slow():
    start_time = time.time()
    time.sleep(random.uniform(1, 3))  # Simulation de latence
    REQUEST_COUNT.labels(endpoint='/slow', status='200').inc()
    LATENCY.labels(endpoint='/slow').observe(time.time() - start_time)
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    return jsonify({'message': 'Réponse lente'})

@app.route('/standard')
def standard():
    REQUEST_COUNT.labels(endpoint='/standard', status='200').inc()
    ERROR_RATE.labels(endpoint='/standard').inc()
    LATENCY.labels(endpoint='/standard').observe(random.uniform(0.15, 0.25)) # between 10ms and 250ms
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    return jsonify({'message': 'Réponse standard'}), 200

@app.route('/errorfast')
def errorfast():
    REQUEST_COUNT.labels(endpoint='/errorfast', status='500').inc()
    ERROR_RATE.labels(endpoint='/errorfast').inc()
    LATENCY.labels(endpoint='/errorfast').observe(random.uniform(0.001, 0.012)) # between 10ms and 120ms
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    return jsonify({'message': 'Erreur simulée fast'}), 500

@app.route('/highdb')
def highdb():
    REQUEST_COUNT.labels(endpoint='/highdb', status='500').inc()
    ERROR_RATE.labels(endpoint='/highdb').inc()
    LATENCY.labels(endpoint='/highdb').observe(random.uniform(1, 2)) # between 10ms and 200ms
    DB_CNX.set(random.uniform(45, 65))  # Simulation de nbre de connexions utilisées
    return jsonify({'message': 'Utilisation haute DB'}), 500

@app.route('/metrics')
def metrics():
    CPU_USAGE.set(random.uniform(10, 90))  # Simulation d'utilisation CPU
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
