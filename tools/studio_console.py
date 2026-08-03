#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio_runtime import StudioService, create_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Production Studio intent console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-root", action="append", default=[])
    parser.add_argument("--sceneforge-runner")
    parser.add_argument("--sceneforge-data-directory")
    args = parser.parse_args()

    service = StudioService(
        ui_root=ROOT / "studio_console",
        allowed_roots=args.allow_root or [Path.cwd()],
        sceneforge_runner=args.sceneforge_runner,
        sceneforge_data_directory=args.sceneforge_data_directory,
    )
    server = create_server(service, args.host, args.port)
    print(f"Production Studio intent console: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
