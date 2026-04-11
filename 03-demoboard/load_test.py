#!/usr/bin/env python3

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request


API_BASE_URL = os.getenv("DEMOBOARD_API_URL", "http://localhost:8000").rstrip("/")
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 3
START_JOB_PROBABILITY = 0.4
MAX_TASK_COUNT = 10
PRUNE_PROBABILITY = 0.15

ADJECTIVES = [
    "blue",
    "fast",
    "silent",
    "curious",
    "lucky",
    "steady",
    "bright",
    "random",
]

NOUNS = [
    "otter",
    "falcon",
    "comet",
    "task",
    "signal",
    "trace",
    "worker",
    "board",
]


def _request(path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict | str]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw_body = response.read().decode("utf-8")
            if not raw_body:
                return response.status, ""
            return response.status, json.loads(raw_body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        return exc.code, error_body


def _random_title() -> str:
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.randint(1000, 9999)}"


def _list_tasks() -> list[dict]:
    status, payload = _request("/tasks")
    if status != 200 or not isinstance(payload, list):
        print(f"[ERROR] task listing failed ({status}): {payload}")
        return []
    return payload


def _prune_tasks() -> None:
    tasks = _list_tasks()
    if len(tasks) <= MAX_TASK_COUNT:
        return

    deletable_tasks = [
        task for task in tasks if task.get("status") in {"pending", "completed"}
    ]
    if not deletable_tasks:
        return

    excess_count = len(tasks) - MAX_TASK_COUNT
    # Prefer deleting the oldest completed tasks first to keep the board small.
    deletable_tasks.sort(key=lambda task: (task.get("status") != "completed", task["id"]))

    deleted_count = 0
    for task in deletable_tasks[:excess_count]:
        task_id = task["id"]
        status, payload = _request(f"/tasks/{task_id}", method="DELETE")
        if status == 204:
            deleted_count += 1
            print(f"[PRUNE] task_id={task_id}")
        else:
            print(f"[ERROR] prune failed for task_id={task_id} ({status}): {payload}")

    if deleted_count:
        print(f"[PRUNE] deleted={deleted_count} remaining_target={MAX_TASK_COUNT}")


def main() -> int:
    print(f"Starting Demoboard load test against {API_BASE_URL}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            title = _random_title()
            status, payload = _request("/tasks", method="POST", payload={"title": title})
            if status != 201:
                print(f"[ERROR] task creation failed ({status}): {payload}")
            else:
                task_id = payload["id"]
                print(f"[CREATE] task_id={task_id} title={title}")

                if random.random() < START_JOB_PROBABILITY:
                    job_status, job_payload = _request(f"/tasks/{task_id}/start-job", method="POST")
                    if job_status == 200:
                        print(f"[START] task_id={task_id}")
                    else:
                        print(f"[ERROR] start-job failed for task_id={task_id} ({job_status}): {job_payload}")

                if random.random() < PRUNE_PROBABILITY:
                    _prune_tasks()

            sleep_for = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("\nLoad test stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
