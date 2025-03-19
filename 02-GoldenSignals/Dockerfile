FROM python:3.9
WORKDIR /app
RUN pip install flask prometheus_client
COPY app.py .
CMD ["python", "app.py"]
