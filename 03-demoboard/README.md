# Demoboard Observability

Ce labo collecte l'observabilité de `tpcs-demoboard` :

- traces et métriques OTEL via `otel-collector`
- logs JSON applicatifs via Fluent Bit vers OpenSearch
- métriques PostgreSQL et Redis via exporters dédiés

## Démarrage

1. Lancer la stack monitoring :

```bash
cd tp-cs-monitoring-student/03-demoboard
docker compose up -d
```

2. Lancer Demoboard avec OTEL activé :

```bash
cd tpcs-demoboard
docker compose up --build -d
```

3. Générer un peu de trafic :

```bash
cd tp-cs-monitoring-student/03-demoboard
python3 load_test.py
```

## Interfaces

- Grafana : http://localhost:3000
- Prometheus : http://localhost:9090
- Jaeger : http://localhost:16686
- OpenSearch Dashboards : http://localhost:5601

Identifiants OpenSearch/OpenSearch Dashboards :

- utilisateur : `admin`
- mot de passe : `Str0ng!DemoBoard#2026`

## Notes pédagogiques

- Les services `api-service` et `worker-service` exportent traces et métriques en OTLP HTTP vers `http://host.docker.internal:4318`.
- Les logs applicatifs sont écrits dans `tpcs-demoboard/observability-logs/`, puis collectés par Fluent Bit.
- PostgreSQL et Redis ne sont pas modifiés : leurs métriques sont exposées par `postgres-exporter` et `redis-exporter`.
- Grafana expose les datasources `Prometheus`, `Jaeger` et `OpenSearch`.
- `load_test.py` simule les actions du frontend en appelant directement l'API Demoboard : création de tâches aléatoires toutes les 1 à 3 secondes, déclenchement aléatoire de certains traitements, et suppression ponctuelle de tâches existantes pour éviter une croissance infinie.

## Variante LGTM

Une variante de test basée sur `grafana/otel-lgtm` est disponible dans `docker-compose.lgtm.yaml`.

- elle écoute sur les mêmes ports utiles côté application : `3000`, `4317`, `4318`, `9090`
- il n'y a donc rien à changer dans `tpcs-demoboard`
- elle ne doit simplement pas tourner en même temps que la stack `03-demoboard`
- elle ajoute `promtail` pour pousser les logs Demoboard vers Loki à partir de `tpcs-demoboard/observability-logs/`
- Grafana importe automatiquement au démarrage le dashboard `Demoboard LGTM Overview`

```bash
docker compose -f docker-compose.lgtm.yaml up -d
python3 load_test.py
```
