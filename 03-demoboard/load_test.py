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
DELETE_TASK_PROBABILITY = 0.25

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


def _delete_random_task() -> None:
    tasks = _list_tasks()
    if not tasks:
        return

    deletable_tasks = [task for task in tasks if task.get("status") != "processing"]
    if not deletable_tasks:
        return

    task = random.choice(deletable_tasks)
    task_id = task["id"]
    status, payload = _request(f"/tasks/{task_id}", method="DELETE")
    if status == 204:
        print(f"[DELETE] task_id={task_id}")
    else:
        print(f"[ERROR] delete failed for task_id={task_id} ({status}): {payload}")


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

                if random.random() < DELETE_TASK_PROBABILITY:
                    _delete_random_task()

            sleep_for = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("\nLoad test stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
