FROM python:3.11-slim
WORKDIR /app
COPY alert_webhook.py .
RUN pip install flask
CMD ["python", "alert_webhook.py"]
