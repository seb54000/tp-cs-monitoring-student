
from flask import Flask, request, Response, jsonify
import time
import random, logging
from prometheus_client import start_http_server, Counter, Histogram, Gauge, generate_latest
from pythonjsonlogger import jsonlogger
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Définition des ressources OpenTelemetry
resource = Resource.create({"service.name": "slow-api"})
# Définition du TracerProvider AVANT l'instrumentation
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)
# Ajout de l'exporteur OTLP pour envoyer les traces à Jaeger
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrumentation Flask et Requests (APRES avoir défini le TracerProvider)
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
# Création du Tracer
tracer = trace.get_tracer(__name__)

# Définition des métriques Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total des requêtes', ['endpoint', 'status'])
LATENCY = Histogram('http_request_duration_seconds', 'Durée des requêtes', ['endpoint'])
ERROR_RATE = Counter('http_errors_total', 'Total des erreurs HTTP', ['endpoint'])
CPU_USAGE = Gauge('cpu_usage', 'Utilisation du CPU (%)')
DB_CNX = Gauge('database_connexions', 'Nbre de connexions simultanées')

CONTENT_TYPE_LATEST = str('text/plain; version=0.0.4; charset=utf-8')

# Configuration du logger JSON
logfile = "/app/logs/app.log"
logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(message)s %(pathname)s %(funcName)s %(lineno)d')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

@app.route('/fast')
def fast():
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/fast', status='200').inc()
    LATENCY.labels(endpoint='/fast').observe(time.time() - start_time)
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    logger.info(f"Request successful for user_id=%s={random.uniform(16, 44)}")
    return jsonify({'message': 'Réponse rapide'})

@app.route('/slow')
def slow():
    start_time = time.time()
    time.sleep(random.uniform(1, 3))  # Simulation de latence
    REQUEST_COUNT.labels(endpoint='/slow', status='200').inc()
    LATENCY.labels(endpoint='/slow').observe(time.time() - start_time)
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    logger.info(f"Request successful for user_id=%s={random.uniform(16, 44)}")
    return jsonify({'message': 'Réponse lente'})

@app.route('/standard')
def standard():
    REQUEST_COUNT.labels(endpoint='/standard', status='200').inc()
    ERROR_RATE.labels(endpoint='/standard').inc()
    LATENCY.labels(endpoint='/standard').observe(random.uniform(0.15, 0.25)) # between 10ms and 200ms
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    logger.info(f"Request successful for user_id=%s={random.uniform(16, 44)}")
    return jsonify({'message': 'Réponse standard'}), 200

@app.route('/errorfast')
def errorfast():
    REQUEST_COUNT.labels(endpoint='/errorfast', status='500').inc()
    ERROR_RATE.labels(endpoint='/errorfast').inc()
    LATENCY.labels(endpoint='/errorfast').observe(random.uniform(0.001, 0.02)) # between 10ms and 200ms
    DB_CNX.set(random.uniform(30, 40))  # Simulation de nbre de connexions utilisées
    logger.error(f"Request failed - error 404 while calling remote service01")
    return jsonify({'message': 'Erreur simulée fast'}), 500

@app.route('/error')
def error():
    REQUEST_COUNT.labels(endpoint='/error', status='500').inc()
    ERROR_RATE.labels(endpoint='/error').inc()
    LATENCY.labels(endpoint='/error').observe(random.uniform(1, 2)) # between 10ms and 200ms
    DB_CNX.set(random.uniform(45, 65))  # Simulation de nbre de connexions utilisées
    error_messages = [
        "Request failed - error 404 while calling remote service01",
        "Request failed - timeout when reaching service02",
        "Request failed - 500 Internal Server Error on backend",
        "Request failed - DNS resolution error for service03",
        "Request failed - OutOfMemory while computing result",
        "Request failed - CPU starvation, resources are low"
    ]
    random_error = random.choice(error_messages)
    logger.error(random_error)
    return jsonify({'message': 'Erreur simulée variable'}), 500

@app.route('/highdb')
def highdb():
    REQUEST_COUNT.labels(endpoint='/highdb', status='500').inc()
    ERROR_RATE.labels(endpoint='/highdb').inc()
    LATENCY.labels(endpoint='/highdb').observe(random.uniform(1, 2)) # between 10ms and 200ms
    DB_CNX.set(random.uniform(45, 65))  # Simulation de nbre de connexions utilisées
    logger.error(f"Request failed / slow - Max connection reached in daabase connexion pool")
    return jsonify({'message': 'Utilisation haute DB'}), 500


def step_1():
    """ Étape rapide (100-200ms) """
    time.sleep(random.uniform(0.1, 0.2))

def step_2():
    """ Étape avec un délai variable (200-1500ms) """
    time.sleep(random.uniform(0.2, 1.5))

def step_3():
    """ Autre étape rapide (100-200ms) """
    time.sleep(random.uniform(0.1, 0.2))

@app.route("/microservices")
def slow_response():
    with tracer.start_as_current_span("step_1"):
        step_1()

    with tracer.start_as_current_span("step_2 (variable delay)"):
        step_2()

    with tracer.start_as_current_span("step_3"):
        step_3()

    return {"message": "long answer"}, 200


@app.route('/metrics')
def metrics():
    CPU_USAGE.set(random.uniform(10, 90))  # Simulation d'utilisation CPU
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
