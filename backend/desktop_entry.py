"""Frozen desktop sidecar entry point configured before importing the app."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-data-dir", required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def _configure(app_data_dir: str, launch_token: str) -> None:
    os.environ["AI_LINKEDIN_RUNTIME_MODE"] = "desktop"
    os.environ["AI_LINKEDIN_APP_DATA_DIR"] = app_data_dir
    os.environ["AI_LINKEDIN_LAUNCH_TOKEN"] = launch_token
    os.environ["PRODUCTION_MODE"] = "true"


async def _check(app_data_dir: str, launch_token: str) -> None:
    _configure(app_data_dir, launch_token)
    from app.main import app

    async with app.router.lifespan_context(app):
        print(json.dumps({"event": "check-complete"}), flush=True)


async def _serve(app_data_dir: str, launch_token: str) -> None:
    _configure(app_data_dir, launch_token)

    import uvicorn
    from app.main import app

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = int(listener.getsockname()[1])
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="info", access_log=False, lifespan="on")
    )
    task = asyncio.create_task(server.serve(sockets=[listener]))
    while not server.started and not task.done():
        await asyncio.sleep(0.025)
    if task.done():
        await task
        raise RuntimeError("Desktop backend stopped before becoming ready")
    print(json.dumps({"event": "ready", "origin": f"http://127.0.0.1:{port}"}), flush=True)
    await task


def main() -> int:
    args = _arguments()
    launch_token = sys.stdin.readline().strip()
    if len(launch_token) < 32:
        print("Desktop launch token was not supplied securely", file=sys.stderr)
        return 2
    try:
        operation = _check if args.check else _serve
        asyncio.run(operation(args.app_data_dir, launch_token))
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Desktop backend failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
