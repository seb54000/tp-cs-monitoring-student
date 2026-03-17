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


def main() -> None:
    wait_for_grafana()
    for path in sorted(Path("/dashboards").glob("*.json")):
        import_dashboard(path)


if __name__ == "__main__":
    main()
