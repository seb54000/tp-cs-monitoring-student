FROM python:3.9
WORKDIR /app
COPY app.py .
RUN pip install requests flask opentelemetry-sdk opentelemetry-instrumentation-flask \
opentelemetry-exporter-prometheus opentelemetry-exporter-jaeger \
opentelemetry-instrumentation-requests opentelemetry-exporter-otlp prometheus_client
CMD ["python", "app.py"]
