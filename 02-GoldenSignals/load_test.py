import requests
import time
import random
import argparse


def get_scenario_config(scenario_id):
    if scenario_id == "1":
        return {
            "main_urls": ["http://localhost:5000/fast", "http://localhost:5000/standard", "http://localhost:5000/errorfast"],
            "secondary_urls": ["http://localhost:5000/slow"],
            "secondary_percent": 2
        }
    elif scenario_id == "2":
        return {
            "main_urls": ["http://localhost:5000/standard"],
            "secondary_urls": ["http://localhost:5000/slow", "http://localhost:5000/fast", "http://localhost:5000/errorfast"],
            "secondary_percent": 5
        }
    elif scenario_id == "3":
        return {
            "main_urls": ["http://localhost:5000/highdb"],
            "secondary_urls": ["http://localhost:5000/slow", "http://localhost:5000/fast", "http://localhost:5000/errorfast"],
            "secondary_percent": 5
        }
    else:
        raise ValueError(f"Scénario inconnu: {scenario_id}")

parser = argparse.ArgumentParser(description="Traffic generator for HTTP endpoints")

parser.add_argument("--scenario", type=str, required=True,
                    help="Numéro du scénario à exécuter (ex: 1, 2, 3...)")
args = parser.parse_args()

try:
    config = get_scenario_config(args.scenario)
except ValueError as e:
    print(e)
    exit(1)

main_urls = config["main_urls"]
secondary_urls = config["secondary_urls"]
secondary_percent = config["secondary_percent"]

print(f"Scénario {args.scenario} chargé avec {len(main_urls)} URL principales "
      f"et {len(secondary_urls)} URL secondaires (usage: {secondary_percent}%)")

# Boucle principale
while True:
    use_secondary = random.uniform(0, 100) < secondary_percent and secondary_urls
    url = random.choice(secondary_urls if use_secondary else main_urls)

    try:
        response = requests.get(url)
        print(f"Requête vers {url} - Status: {response.status_code}")
    except Exception as e:
        print(f"Erreur lors de l'appel {url}: {e}")

    time.sleep(random.uniform(0.5, 0.6))