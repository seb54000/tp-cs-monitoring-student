import requests
import time
import random

URLS = ["http://localhost:5000/slow"]
# URLS = ["http://localhost:8000/slow", "http://flask-app/slow", "http://flask-app/error"]

while True:
    url = random.choice(URLS)
    try:
        response = requests.get(url)
        print(f"Requête vers {url} - Status: {response.status_code} - {response.content} ")
    except Exception as e:
        print(f"Erreur lors de l'appel {url}: {e}")

    time.sleep(random.uniform(0.5, 2))
