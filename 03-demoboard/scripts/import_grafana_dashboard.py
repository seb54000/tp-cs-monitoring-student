import json
import time
import urllib.error
import urllib.request
from pathlib import Path


GRAFANA_URL = "http://lgtm:3000"
AUTH_HEADER = "Basic YWRtaW46YWRtaW4="


def wait_for_grafana(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/health",
        headers={"Authorization": AUTH_HEADER},
    )
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("Grafana did not become ready in time")


def wait_for_datasource(uid: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/{uid}",
        headers={"Authorization": AUTH_HEADER},
    )
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    print(f"Datasource ready: {uid}", flush=True)
                    return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                print(f"Datasource {uid} not ready yet: HTTP {exc.code}", flush=True)
        except Exception as exc:
            print(f"Datasource {uid} not ready yet: {exc}", flush=True)
        time.sleep(2)
    raise RuntimeError(f"Datasource {uid} did not become ready in time")


def import_dashboard(path: Path) -> None:
    payload = json.dumps(
        {
            "dashboard": json.loads(path.read_text()),
            "folderId": 0,
            "overwrite": True,
        }
    ).encode()
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/dashboards/db",
        data=payload,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode())
    print(f"Imported {path.name}: {body['status']} ({body['uid']})")


def update_tempo_traces_to_logs() -> None:
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/tempo",
        headers={"Authorization": AUTH_HEADER},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        datasource = json.loads(response.read().decode())

    json_data = datasource.get("jsonData", {})
    traces_to_logs = json_data.get("tracesToLogsV2", {})
    traces_to_logs.update(
        {
            "customQuery": True,
            "datasourceUid": "loki",
            "query": "{${__tags}} | json | trace_id = \"${__trace.traceId}\"",
            "spanStartTimeShift": "-5m",
            "spanEndTimeShift": "5m",
            "tags": [{"key": "service.name", "value": "service_name"}],
        }
    )
    json_data["tracesToLogsV2"] = traces_to_logs
    json_data["tracesToMetrics"] = {
        "datasourceUid": "prometheus",
        "spanStartTimeShift": "-15m",
        "spanEndTimeShift": "15m",
        "tags": [{"key": "service.name", "value": "service"}],
        "queries": [
            {
                "name": "Span rate",
                "query": 'sum(rate(traces_spanmetrics_calls_total{$__tags, span_name="${__span.name}"}[5m]))',
            },
            {
                "name": "Span p95 latency",
                "query": 'histogram_quantile(0.95, sum by (le) (rate(traces_spanmetrics_latency_bucket{$__tags, span_name="${__span.name}"}[5m])))',
            },
            {
                "name": "Service p95 latency",
                "query": 'histogram_quantile(0.95, sum by (le) (rate(traces_spanmetrics_latency_bucket{$__tags}[5m])))',
            },
        ],
    }
    datasource["jsonData"] = json_data

    payload = json.dumps(
        {
            "name": datasource["name"],
            "type": datasource["type"],
            "access": datasource["access"],
            "url": datasource["url"],
            "basicAuth": datasource.get("basicAuth", False),
            "isDefault": datasource.get("isDefault", False),
            "jsonData": datasource["jsonData"],
        }
    ).encode()

    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/tempo",
        data=payload,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode())
    print(f"Updated Tempo datasource: {body['datasource']['uid']}")


def update_loki_logs_to_traces() -> None:
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/loki",
        headers={"Authorization": AUTH_HEADER},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        datasource = json.loads(response.read().decode())

    json_data = datasource.get("jsonData", {})
    json_data["derivedFields"] = [
        {
            "datasourceUid": "tempo",
            "matcherRegex": '"trace_id":"([0-9a-f]{32})"',
            "name": "trace_id",
            "url": "${__value.raw}",
            "urlDisplayLabel": "Trace: ${__value.raw}",
        }
    ]
    datasource["jsonData"] = json_data

    payload = json.dumps(
        {
            "name": datasource["name"],
            "type": datasource["type"],
            "access": datasource["access"],
            "url": datasource["url"],
            "basicAuth": datasource.get("basicAuth", False),
            "isDefault": datasource.get("isDefault", False),
            "jsonData": datasource["jsonData"],
        }
    ).encode()

    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/loki",
        data=payload,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode())
    print(f"Updated Loki datasource: {body['datasource']['uid']}")


def main() -> None:
    print("Waiting for Grafana...", flush=True)
    wait_for_grafana()
    wait_for_datasource("tempo")
    wait_for_datasource("loki")
    wait_for_datasource("prometheus")
    print("Updating datasources...", flush=True)
    update_tempo_traces_to_logs()
    update_loki_logs_to_traces()
    print("Importing dashboards...", flush=True)
    for path in sorted(Path("/dashboards").glob("*.json")):
        import_dashboard(path)
    print("Grafana bootstrap completed.", flush=True)


if __name__ == "__main__":
    main()
