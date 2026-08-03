#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from studio_runtime import StudioService, create_server


def parse_command(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    command = tuple(shlex.split(value))
    if not command:
        raise argparse.ArgumentTypeError("command must not be empty")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Production Studio intent console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allow-root", action="append", default=[])
    parser.add_argument("--sceneforge-runner")
    parser.add_argument("--sceneforge-data-directory")
    parser.add_argument(
        "--image-generator-command",
        help="Quoted command implementing the JSON-over-stdio image generation adapter contract",
    )
    parser.add_argument(
        "--image-evaluator-command",
        help="Optional quoted command implementing the JSON-over-stdio semantic evaluator contract",
    )
    parser.add_argument(
        "--recreation-output-directory",
        help="Directory where reference-recreation jobs and candidate artifacts are retained",
    )
    args = parser.parse_args()

    service = StudioService(
        ui_root=ROOT / "studio_console",
        allowed_roots=args.allow_root or [Path.cwd()],
        sceneforge_runner=args.sceneforge_runner,
        sceneforge_data_directory=args.sceneforge_data_directory,
        image_generator_command=parse_command(args.image_generator_command),
        image_evaluator_command=parse_command(args.image_evaluator_command),
        recreation_output_directory=args.recreation_output_directory,
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
