from flask import Flask, request
import random
import time
from opentelemetry import trace, metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from prometheus_client import start_http_server

# Initialisation de Flask
app = Flask(__name__)

# Instrumentation OpenTelemetry
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Configuration du Tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))

# Configuration des métriques
reader = PrometheusMetricReader()
metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
meter = metrics.get_meter(__name__)

latency_metric = meter.create_histogram(
    "api_request_latency",
    description="Temps de réponse des requêtes API",
)

@app.route("/slow")
def slow_request():
    with tracer.start_as_current_span("slow_request_span"):
        delay = random.choice([0.1, 0.2, 0.5, 2, 3, 4])  # Simulation de latence aléatoire
        time.sleep(delay)
        
        # Enregistrement des métriques
        latency_metric.record(delay, {"endpoint": "/slow"})
        
        return {"message": "Réponse après un délai"}, 200

if __name__ == "__main__":
    start_http_server(8000)  # Serveur Prometheus
    app.run(host="0.0.0.0", port=5000)
