"""One-command local web/worker launcher with separate credential environments."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import dotenv_values
from pydantic import ValidationError

from app.config import SandboxGuardError, WebSettings, WorkerSettings, validate_product


def stop_child(child: subprocess.Popen[bytes]) -> None:
    """Stop the owned process tree, including Windows virtualenv launcher children."""
    if child.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(child.pid), "/T", "/F"],
            capture_output=True,
            check=False,
            timeout=15,
        )
    else:
        child.terminate()
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def environments(source: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    web = {
        k: v for k, v in source.items() if k not in {"AWX_CLIENT_ID", "AWX_API_KEY", "AWX_LOGIN_AS"}
    }
    worker = {
        k: v for k, v in source.items() if k not in {"ANTHROPIC_API_KEY", "AWX_WEBHOOK_SECRET"}
    }
    return web, worker


def main() -> int:
    try:
        web_settings, worker_settings = WebSettings(), WorkerSettings()
        validate_product(web_settings)
        validate_product(worker_settings)
    except (SandboxGuardError, ValidationError):
        print(
            "Invalid local configuration. Check the documented sandbox, mode and origin settings."
        )
        return 2
    source = {k: v for k, v in dotenv_values(Path(".env")).items() if v is not None}
    source.update(os.environ)
    # Explicit defaults are passed to both children, never inferred from provider data.
    source.setdefault("AWX_ENV", web_settings.awx_env)
    source.setdefault("AWX_BASE_URL", web_settings.awx_base_url)
    source.setdefault("AWX_MODE", web_settings.awx_mode)
    web_env, worker_env = environments(source)
    children: list[subprocess.Popen[bytes]] = []
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        worker = subprocess.Popen(
            [sys.executable, "-m", "app.workers.service"], env=worker_env, creationflags=flags
        )
        children.append(worker)
        web = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.api.main:app",
                "--host",
                web_settings.app_host,
                "--port",
                str(web_settings.app_port),
                "--no-access-log",
            ],
            env=web_env,
            creationflags=flags,
        )
        children.append(web)
        print("Local operations desk: " + web_settings.webauthn_origin, flush=True)
        while web.poll() is None:
            # Missing keys leave a real setup-error heartbeat and a usable setup UI.
            time.sleep(0.25)
        return int(web.returncode or 0)
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            stop_child(child)


if __name__ == "__main__":
    raise SystemExit(main())
