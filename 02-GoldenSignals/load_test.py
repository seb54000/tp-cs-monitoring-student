import requests
import time
import random

URLS = ["http://localhost:5000/fast", "http://localhost:5000/slow", "http://localhost:5000/errorfast"]

while True:
    url = random.choice(URLS)
    try:
        response = requests.get(url)
        print(f"Requête vers {url} - Status: {response.status_code} - {response.content} ")
    except Exception as e:
        print(f"Erreur lors de l'appel {url}: {e}")

    time.sleep(random.uniform(0.5, 0.6))


