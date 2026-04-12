#!/usr/bin/env python3

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request


DEFAULT_API_BASE_URL = os.getenv("DEMOBOARD_API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_MIN_DELAY_SECONDS = 1.0
DEFAULT_MAX_DELAY_SECONDS = 3.0
DEFAULT_START_JOB_PROBABILITY = 0.4
DEFAULT_MAX_TASK_COUNT = 10
DEFAULT_PRUNE_PROBABILITY = 0.15

BURST_MIN_DELAY_SECONDS = 0.2
BURST_MAX_DELAY_SECONDS = 0.2
BURST_START_JOB_PROBABILITY = 0.8
BURST_MAX_TASK_COUNT = 40
BURST_PRUNE_PROBABILITY = 0.08

CURRENT_MIN_DELAY_SECONDS = DEFAULT_MIN_DELAY_SECONDS
CURRENT_MAX_DELAY_SECONDS = DEFAULT_MAX_DELAY_SECONDS
CURRENT_START_JOB_PROBABILITY = DEFAULT_START_JOB_PROBABILITY
CURRENT_MAX_TASK_COUNT = DEFAULT_MAX_TASK_COUNT
CURRENT_PRUNE_PROBABILITY = DEFAULT_PRUNE_PROBABILITY

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


def _request(api_base_url: str, path: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict | str]:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{api_base_url}{path}",
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


def _list_tasks(api_base_url: str) -> list[dict]:
    status, payload = _request(api_base_url, "/tasks")
    if status != 200 or not isinstance(payload, list):
        print(f"[ERROR] task listing failed ({status}): {payload}")
        return []
    return payload


def _prune_tasks(api_base_url: str) -> None:
    tasks = _list_tasks(api_base_url)
    if len(tasks) <= CURRENT_MAX_TASK_COUNT:
        return

    deletable_tasks = [
        task for task in tasks if task.get("status") in {"pending", "completed"}
    ]
    if not deletable_tasks:
        return

    excess_count = len(tasks) - CURRENT_MAX_TASK_COUNT
    # Prefer deleting the oldest completed tasks first to keep the board small.
    deletable_tasks.sort(key=lambda task: (task.get("status") != "completed", task["id"]))

    deleted_count = 0
    for task in deletable_tasks[:excess_count]:
        task_id = task["id"]
        status, payload = _request(api_base_url, f"/tasks/{task_id}", method="DELETE")
        if status == 204:
            deleted_count += 1
            print(f"[PRUNE] task_id={task_id}")
        else:
            print(f"[ERROR] prune failed for task_id={task_id} ({status}): {payload}")

    if deleted_count:
        print(f"[PRUNE] deleted={deleted_count} remaining_target={CURRENT_MAX_TASK_COUNT}")


def _resolve_api_base_url() -> str:
    parser = argparse.ArgumentParser(
        description="Generate synthetic traffic against the Demoboard API."
    )
    parser.add_argument(
        "api_base_url",
        nargs="?",
        default=DEFAULT_API_BASE_URL,
        help="Demoboard API base URL. Default: %(default)s",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Use a faster high-volume profile intended for the scaled v2 deployment.",
    )
    return parser.parse_args()


def main() -> int:
    global CURRENT_MIN_DELAY_SECONDS
    global CURRENT_MAX_DELAY_SECONDS
    global CURRENT_START_JOB_PROBABILITY
    global CURRENT_MAX_TASK_COUNT
    global CURRENT_PRUNE_PROBABILITY

    args = _resolve_api_base_url()
    api_base_url = args.api_base_url.rstrip("/")

    if args.burst:
        CURRENT_MIN_DELAY_SECONDS = BURST_MIN_DELAY_SECONDS
        CURRENT_MAX_DELAY_SECONDS = BURST_MAX_DELAY_SECONDS
        CURRENT_START_JOB_PROBABILITY = BURST_START_JOB_PROBABILITY
        CURRENT_MAX_TASK_COUNT = BURST_MAX_TASK_COUNT
        CURRENT_PRUNE_PROBABILITY = BURST_PRUNE_PROBABILITY
        profile_name = "burst"
    else:
        CURRENT_MIN_DELAY_SECONDS = DEFAULT_MIN_DELAY_SECONDS
        CURRENT_MAX_DELAY_SECONDS = DEFAULT_MAX_DELAY_SECONDS
        CURRENT_START_JOB_PROBABILITY = DEFAULT_START_JOB_PROBABILITY
        CURRENT_MAX_TASK_COUNT = DEFAULT_MAX_TASK_COUNT
        CURRENT_PRUNE_PROBABILITY = DEFAULT_PRUNE_PROBABILITY
        profile_name = "default"

    print(f"Starting Demoboard load test against {api_base_url}")
    print(
        f"Profile={profile_name} delay={CURRENT_MIN_DELAY_SECONDS:.1f}-{CURRENT_MAX_DELAY_SECONDS:.1f}s "
        f"start_job_probability={CURRENT_START_JOB_PROBABILITY:.2f} "
        f"max_tasks={CURRENT_MAX_TASK_COUNT} prune_probability={CURRENT_PRUNE_PROBABILITY:.2f}"
    )
    print("Press Ctrl+C to stop.")

    try:
        while True:
            title = _random_title()
            status, payload = _request(api_base_url, "/tasks", method="POST", payload={"title": title})
            if status != 201:
                print(f"[ERROR] task creation failed ({status}): {payload}")
            else:
                task_id = payload["id"]
                print(f"[CREATE] task_id={task_id} title={title}")

                if random.random() < CURRENT_START_JOB_PROBABILITY:
                    job_status, job_payload = _request(api_base_url, f"/tasks/{task_id}/start-job", method="POST")
                    if job_status == 200:
                        print(f"[START] task_id={task_id}")
                    else:
                        print(f"[ERROR] start-job failed for task_id={task_id} ({job_status}): {job_payload}")

                if random.random() < CURRENT_PRUNE_PROBABILITY:
                    _prune_tasks(api_base_url)

            sleep_for = random.uniform(CURRENT_MIN_DELAY_SECONDS, CURRENT_MAX_DELAY_SECONDS)
            time.sleep(sleep_for)
    except KeyboardInterrupt:
        print("\nLoad test stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
