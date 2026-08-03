#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def emit(message: str, progress: float) -> None:
    print(json.dumps({
        "kind": "video.adapter-event",
        "message": message,
        "progress": progress,
    }), flush=True)


def fail(message: str, code: int = 1) -> int:
    print(json.dumps({"status": "failed", "error": message}), flush=True)
    return code


def dimensions(value: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in value.lower().split("x", 1))
    except Exception as exc:
        raise ValueError(f"invalid size: {value}") from exc
    if width < 64 or height < 64:
        raise ValueError("video dimensions are too small")
    return width, height


def run(command: list[str]) -> None:
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode:
        raise RuntimeError(process.stderr[-4000:] or f"command exited with {process.returncode}")


def generate(request: dict[str, Any], output: Path) -> Path:
    reference = Path(str(request["reference_image"])).expanduser().resolve()
    if not reference.is_file():
        raise FileNotFoundError(f"reference image does not exist: {reference}")
    width, height = dimensions(str(request.get("size", "1280x720")))
    seconds = int(request.get("seconds", 4))
    fps = int(request.get("fps", 24))
    frames = seconds * fps
    candidate = str(request.get("candidate_id", "candidate"))
    destination = output / f"{candidate}.mp4"

    # Dense local synthesis: continuous camera path, light breathing, temporal denoise,
    # and exact frame count. It consumes only local runtime CPU and ffmpeg.
    zoom_delta = 0.055 if candidate.endswith("2") else 0.038
    x_drift = 18 if candidate.endswith("2") else 10
    vf = (
        f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
        f"crop={width*2}:{height*2},"
        f"zoompan=z='1+{zoom_delta}*on/{max(1, frames-1)}':"
        f"x='iw/2-(iw/zoom/2)+{x_drift}*sin(on/28)':"
        f"y='ih/2-(ih/zoom/2)+4*sin(on/37)':"
        f"d={frames}:s={width}x{height}:fps={fps},"
        "eq=contrast=1.035:saturation=1.025:brightness='0.006*sin(2*PI*t/2.4)',"
        "hqdn3d=1.0:1.0:3.0:3.0,unsharp=5:5:0.32:3:3:0.0,format=yuv420p"
    )
    emit("Local runtime accepted the dense shot.", 0.08)
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(reference),
        "-vf", vf, "-frames:v", str(frames), "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-movflags", "+faststart", str(destination),
    ])
    emit("Local dense frames encoded.", 0.92)
    return destination


def repair(request: dict[str, Any], output: Path) -> Path:
    parent = Path(str(request["parent_video"])).expanduser().resolve()
    if not parent.is_file():
        raise FileNotFoundError(f"parent video does not exist: {parent}")
    width, height = dimensions(str(request.get("size", "1280x720")))
    candidate = str(request.get("candidate_id", "repair"))
    destination = output / f"{candidate}.mp4"
    issues = {str(value) for value in request.get("repair_issues", [])}

    filters = [f"scale={width}:{height}:flags=lanczos"]
    if "temporal_consistency" in issues or "artifact_penalty" in issues:
        filters.extend(["hqdn3d=1.35:1.35:4.2:4.2", "deflicker=size=5:mode=am"])
    if "motion_quality" in issues:
        filters.append("minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
    if "composition" in issues or "camera_intent" in issues:
        filters.append("crop=iw*0.985:ih*0.985:(iw-ow)/2:(ih-oh)/2")
        filters.append(f"scale={width}:{height}:flags=lanczos")
    filters.extend(["unsharp=5:5:0.24:3:3:0.0", "format=yuv420p"])

    emit("Local repair pass started.", 0.12)
    run([
        "ffmpeg", "-y", "-i", str(parent), "-vf", ",".join(filters),
        "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-movflags", "+faststart", str(destination),
    ])
    emit("Local repair pass encoded.", 0.94)
    return destination


def main() -> int:
    try:
        request = json.load(sys.stdin)
        output = Path(str(request["output_directory"])).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        if not shutil.which("ffmpeg"):
            return fail("ffmpeg is required for the local runtime adapter")
        operation = str(request.get("operation", "generate_video"))
        if operation == "generate_video":
            path = generate(request, output)
        elif operation == "repair_video":
            path = repair(request, output)
        else:
            return fail(f"unsupported operation: {operation}")
        try:
            path.resolve().relative_to(output)
        except ValueError:
            return fail("local adapter output escaped the assigned directory")
        print(json.dumps({
            "status": "completed",
            "video_path": str(path.resolve()),
            "provider_job_id": None,
            "runtime": "local-ffmpeg",
            "account_required": False,
        }), flush=True)
        return 0
    except Exception as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
