# LGTM — images de référence du 1er octobre 2026

Les images LGTM, Python (Compose) et Promtail sont référencées par digest
linux/amd64. LGTM et Python proviennent des images observées sur EKS ; Promtail
3.6.1 a seulement été résolu au registre : aucun DaemonSet Promtail ne tournait
lors du relevé. Sa collecte de logs reste donc à valider.

Les helpers de `tpcs-workstations` figent également les images Demoboard,
PostgreSQL, Redis, kubectl et le job Python de bootstrap Grafana. Le rapport et
le verrou détaillés sont dans ce dépôt :
`versions/baselines/tpmon-2026-10-01/README.md` et `images.lock.json`.

Ce gel concerne les images de la stack LGTM, pas la reproductibilité des builds
Demoboard en Compose ni les autres exercices. Conserver les artefacts ECR avant
destruction de leur dépôt. Le redéploiement, les métriques, traces et logs restent
à retester ; aucune stack en cours n'a été modifiée pour appliquer ces fichiers.
