from flask import Flask, request
import random
import time
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_client import start_http_server, generate_latest
from flask import Response

# Définition des ressources OpenTelemetry
resource = Resource.create({"service.name": "slow-api"})

# ✅ Définition du TracerProvider AVANT l'instrumentation
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# ✅ Ajout de l'exporteur OTLP pour envoyer les traces à Jaeger
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# ✅ Instrumentation Flask et Requests (APRES avoir défini le TracerProvider)
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Création du Tracer
tracer = trace.get_tracer(__name__)

# Définition du MetricReader et enregistrement dans OpenTelemetry
reader = PrometheusMetricReader()
meter_provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

latency_metric = meter.create_histogram(
    "api_request_latency",
    description="Temps de réponse des requêtes API",
)

@app.route("/slow")
def slow_request():
    with tracer.start_as_current_span("slow_request_span"):
        delay = random.choice([0.1, 0.2, 0.5, 2, 3, 4])
        time.sleep(delay)
        latency_metric.record(delay, {"endpoint": "/slow"})
        return {"message": "delay {}".format(delay)}, 200


@app.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), mimetype="text/plain")

def step_1():
    """ Étape rapide (100-200ms) """
    time.sleep(random.uniform(0.1, 0.2))

def step_2():
    """ Étape avec un délai variable (200-1500ms) """
    time.sleep(random.uniform(0.2, 1.5))

def step_3():
    """ Autre étape rapide (100-200ms) """
    time.sleep(random.uniform(0.1, 0.2))

@app.route("/slowing")
def slow_response():
    with tracer.start_as_current_span("step_1"):
        step_1()
    
    with tracer.start_as_current_span("step_2 (variable delay)"):
        step_2()

    with tracer.start_as_current_span("step_3"):
        step_3()

    return {"message": "Réponse après un traitement long"}, 200



if __name__ == "__main__":
    start_http_server(8000)  # Serveur Prometheus
    app.run(host="0.0.0.0", port=5000)
