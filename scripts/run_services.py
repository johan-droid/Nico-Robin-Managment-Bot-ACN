"""Run the bot and background services together for local development.

Usage:
    python scripts/run_services.py

By default this starts:
    - the Telegram bot
    - the Celery worker
    - the Celery beat scheduler

You can override the service list with --services.
"""

from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass


def _safe_print(message: str) -> None:
    """Print launcher output without crashing on console encoding issues."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoded = message.encode("utf-8", errors="backslashreplace")
        print(encoded.decode(sys.stdout.encoding or "utf-8", errors="backslashreplace"))


@dataclass(frozen=True)
class ServiceCommand:
    name: str
    args: list[str]


DEFAULT_SERVICES: tuple[str, ...] = ("bot", "worker", "beat")


def _build_service_command(name: str) -> ServiceCommand:
    if name == "bot":
        return ServiceCommand(
            name="bot",
            args=[sys.executable, "-m", "src.bot.main"],
        )
    if name == "worker":
        worker_args = [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "src.bot.tasks.celery_app:celery_app",
            "worker",
            "--loglevel=info",
        ]
        if os.name == "nt":
            worker_args.extend(["--pool=solo", "--concurrency=1"])
        return ServiceCommand(name="worker", args=worker_args)
    if name == "beat":
        return ServiceCommand(
            name="beat",
            args=[
                sys.executable,
                "-m",
                "celery",
                "-A",
                "src.bot.tasks.celery_app:celery_app",
                "beat",
                "--loglevel=info",
            ],
        )
    raise ValueError(f"Unknown service: {name}")


def _stream_output(name: str, stream: io.TextIOWrapper) -> None:
    for line in iter(stream.readline, ""):
        if not line:
            break
        _safe_print(f"[{name}] {line.rstrip()}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--services",
        nargs="+",
        choices=("bot", "worker", "beat"),
        default=list(DEFAULT_SERVICES),
        help="Services to run concurrently.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    processes: list[tuple[str, subprocess.Popen[str]]] = []
    threads: list[threading.Thread] = []

    try:
        for service_name in args.services:
            command = _build_service_command(service_name)
            process = subprocess.Popen(
                command.args,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
            processes.append((command.name, process))
            _safe_print(f"[{command.name}] started pid={process.pid}")
            if process.stdout is not None:
                stream = io.TextIOWrapper(
                    process.stdout,
                    encoding="utf-8",
                    errors="replace",
                    newline="",
                )
                thread = threading.Thread(
                    target=_stream_output,
                    args=(command.name, stream),
                    daemon=True,
                )
                thread.start()
                threads.append(thread)

        exit_code = 0
        while processes:
            for service_name, process in list(processes):
                result = process.poll()
                if result is None:
                    continue
                if result != 0 and exit_code == 0:
                    exit_code = result
                _safe_print(f"[{service_name}] exited with code {result}")
                processes.remove((service_name, process))
                if processes:
                    _safe_print("[launcher] stopping remaining services")
                return exit_code
            time.sleep(0.5)
        return exit_code
    except KeyboardInterrupt:
        _safe_print("[launcher] shutdown requested")
        return 130
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except Exception:
                    process.kill()
        for thread in threads:
            thread.join(timeout=1)


if __name__ == "__main__":
    raise SystemExit(main())
