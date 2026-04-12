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
- Le worker Demoboard simule par défaut un temps de traitement aléatoire entre `1.5` et `2.7` secondes, ajustable via `WORKER_PROCESSING_TIME_MIN_SECONDS` et `WORKER_PROCESSING_TIME_MAX_SECONDS`.
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
- le panneau `Worker Latency` affiche la latence des traitements worker avec des exemplars OTEL permettant d'ouvrir des traces Tempo

```bash
docker compose -f docker-compose.lgtm.yaml up -d
python3 load_test.py
```

## Déploiement Kubernetes EKS

Deux bundles Kubernetes sont fournis dans [`kubernetes`](tp-cs-monitoring-student/03-demoboard/kubernetes) :

- [`monitoring-classic.eks.yaml`](tp-cs-monitoring-student/03-demoboard/kubernetes/monitoring-classic.eks.yaml) pour `OTEL Collector + Prometheus + Grafana + Jaeger + OpenSearch`
- [`monitoring-lgtm.eks.yaml`](tp-cs-monitoring-student/03-demoboard/kubernetes/monitoring-lgtm.eks.yaml) pour `grafana/otel-lgtm + promtail`
- côté Demoboard, deux manifests sont fournis à la racine du dépôt source :
  - `demoboard-kubernetes-observability.yml` pour le mode initial `v1`
  - `demoboard-kubernetes-observability-scaled.yml` pour le mode `v2` scalé

Caractéristiques :

- namespace cible : `vmXX`
- les deux variantes exposent le même endpoint OTLP interne : `otel-collector.vmXX.svc.cluster.local`
- les logs sont collectés depuis les logs conteneurs Kubernetes via `DaemonSet`, pas via un montage local
- les manifests ajoutent un enrichissement Kubernetes : pod, namespace, node, container et, selon la variante, deployment
- les ingress utilisent par défaut le wildcard TLS EKS sous la forme `service-vmXX.eksYY.<dns_subdomain>` avec le secret `tls-certificate`
- les PVC supposent une `StorageClass` par défaut dans EKS
- un mémo de commandes est généré sur chaque VM étudiante dans `~/tpmon_eks_demoboard_monitoring_lgtm.txt`

Exemple :

```bash
eks apply -f 03-demoboard/kubernetes/monitoring-classic.eks.yaml
# ou
eks apply -f 03-demoboard/kubernetes/monitoring-lgtm.eks.yaml
```

Pour que Demoboard envoie ses traces et métriques vers la stack EKS, il faut pointer son export OTLP vers :

```text
http://otel-collector.vmXX.svc.cluster.local:4318
```

Les exporters `postgres` et `redis` de la variante classique ciblent les services Kubernetes suivants, attendus dans le namespace `vmXX` :

- `postgres.vmXX.svc.cluster.local:5432`
- `redis.vmXX.svc.cluster.local:6379`

## Changelog

- 2026-04-12 : `load_test.py` accepte désormais une URL API en argument positionnel, en plus de `DEMOBOARD_API_URL`, ce qui permet de générer du trafic directement vers un déploiement Demoboard sur EKS avec `python3 load_test.py https://.../api`.
