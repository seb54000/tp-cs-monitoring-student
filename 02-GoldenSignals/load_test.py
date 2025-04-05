import requests
import time
import random
import argparse

parser = argparse.ArgumentParser(description="Traffic generator for HTTP endpoints")

# parser.add_argument("--main-urls", nargs="+", required=True,
#                     help="Liste des URLs principales")
# parser.add_argument("--secondary-urls", nargs="+", default=[],
#                     help="Liste des URLs secondaires (optionnelle)")
parser.add_argument("--secondary-percent", type=float, default=0.0,
                    help="Pourcentage d'utilisation des URLs secondaires (0 à 100)")
args = parser.parse_args()

main_urls = ["http://localhost:5000/fast", "http://localhost:5000/standard", "http://localhost:5000/errorfast"]
secondary_urls = ["http://localhost:5000/slow"]
secondary_percent = args.secondary_percent

# scenario 2, should remove errorfast (we have corrected the bug, but now we have more standard request, fast are only a fraction)


while True:
    use_secondary = random.uniform(0, 100) < secondary_percent and secondary_urls
    url = random.choice(secondary_urls if use_secondary else main_urls)
    try:
        response = requests.get(url)
        print(f"Requête vers {url} - Status: {response.status_code} - {response.content} ")
    except Exception as e:
        print(f"Erreur lors de l'appel {url}: {e}")

    time.sleep(random.uniform(0.5, 0.6))


