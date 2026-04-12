import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


GRAFANA_URL = os.getenv("GRAFANA_URL", "http://lgtm:3000")
AUTH_HEADER = os.getenv("GRAFANA_AUTH_HEADER", "Basic YWRtaW46YWRtaW4=")
PROMETHEUS_DATASOURCE_URL = os.getenv("PROMETHEUS_DATASOURCE_URL", "")
TEMPO_DATASOURCE_URL = os.getenv("TEMPO_DATASOURCE_URL", "")
LOKI_DATASOURCE_URL = os.getenv("LOKI_DATASOURCE_URL", "")


def wait_for_grafana(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    print(f"Checking Grafana health at {GRAFANA_URL}/api/health", flush=True)
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/health",
        headers={"Authorization": AUTH_HEADER},
    )
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    print("Grafana health endpoint is ready.", flush=True)
                    return
                print(f"Grafana health returned unexpected HTTP {response.status}", flush=True)
        except urllib.error.HTTPError as exc:
            print(f"Grafana health HTTP error: {exc.code}", flush=True)
        except urllib.error.URLError as exc:
            print(f"Grafana health URL error: {exc.reason}", flush=True)
        except Exception:
            print("Grafana health request failed with unexpected error.", flush=True)
        time.sleep(2)
    raise RuntimeError("Grafana did not become ready in time")


def wait_for_datasource(uid: str, timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    print(f"Checking datasource {uid} at {GRAFANA_URL}/api/datasources/uid/{uid}", flush=True)
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
    print(f"Importing dashboard from {path}", flush=True)
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


def update_datasource_url(uid: str, expected_url: str) -> None:
    if not expected_url:
        return

    print(f"Fetching datasource {uid} to enforce URL {expected_url}.", flush=True)
    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/{uid}",
        headers={"Authorization": AUTH_HEADER},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        datasource = json.loads(response.read().decode())

    datasource["url"] = expected_url

    payload = json.dumps(
        {
            "name": datasource["name"],
            "type": datasource["type"],
            "access": datasource["access"],
            "url": datasource["url"],
            "basicAuth": datasource.get("basicAuth", False),
            "isDefault": datasource.get("isDefault", False),
            "jsonData": datasource.get("jsonData", {}),
        }
    ).encode()

    request = urllib.request.Request(
        f"{GRAFANA_URL}/api/datasources/uid/{uid}",
        data=payload,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode())
    print(f"Updated datasource URL for {uid}: {body['datasource']['url']}", flush=True)


def update_tempo_traces_to_logs() -> None:
    print("Fetching Tempo datasource for traces/logs and traces/metrics configuration.", flush=True)
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
    print("Fetching Loki datasource for logs-to-traces configuration.", flush=True)
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
    print(f"Waiting for Grafana at {GRAFANA_URL}...", flush=True)
    wait_for_grafana()
    wait_for_datasource("tempo")
    wait_for_datasource("loki")
    wait_for_datasource("prometheus")
    update_datasource_url("prometheus", PROMETHEUS_DATASOURCE_URL)
    update_datasource_url("tempo", TEMPO_DATASOURCE_URL)
    update_datasource_url("loki", LOKI_DATASOURCE_URL)
    print("Updating datasources...", flush=True)
    update_tempo_traces_to_logs()
    update_loki_logs_to_traces()
    print("Importing dashboards...", flush=True)
    for path in sorted(Path("/dashboards").glob("*.json")):
        import_dashboard(path)
    print("Grafana bootstrap completed.", flush=True)


if __name__ == "__main__":
    main()
