#!/usr/bin/env python3
"""OpenAI adapter for the Production Studio reference-recreation pipeline.

The process reads one JSON request from stdin and writes one JSON response to stdout.
It supports both `generate` and `evaluate` operations so the studio can configure the
same executable as its generator and evaluator command.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any


def emit(value: dict[str, Any], *, exit_code: int = 0) -> None:
    print(json.dumps(value, ensure_ascii=False))
    raise SystemExit(exit_code)


def data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def retry_after(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        raw = headers.get("retry-after") or headers.get("Retry-After")
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                return None
    return None


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("evaluation output was not an object")
    return value


def main() -> None:
    try:
        from openai import APIStatusError, OpenAI, RateLimitError
    except ImportError:
        emit({"status": "error", "error": "Install the OpenAI Python SDK: python3 -m pip install openai"}, exit_code=2)

    try:
        request = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        emit({"status": "error", "error": f"invalid adapter request: {exc}"}, exit_code=2)

    client = OpenAI()
    operation = request.get("operation")
    try:
        if operation == "generate":
            output_directory = Path(request["output_directory"]).expanduser().resolve()
            output_directory.mkdir(parents=True, exist_ok=True)
            parent_image = Path(request["parent_image"]).expanduser().resolve()
            prompt = str(request["prompt"])
            kwargs: dict[str, Any] = {
                "model": os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
                "image": parent_image.open("rb"),
                "prompt": prompt,
                "size": os.getenv("OPENAI_IMAGE_SIZE", "1536x1024"),
                "quality": os.getenv("OPENAI_IMAGE_QUALITY", "high"),
                "input_fidelity": os.getenv("OPENAI_IMAGE_INPUT_FIDELITY", "high"),
            }
            try:
                response = client.images.edit(**kwargs)
            finally:
                kwargs["image"].close()
            encoded = response.data[0].b64_json
            if not encoded:
                emit({"status": "error", "error": "image response did not include b64_json"}, exit_code=2)
            image_path = output_directory / "candidate.png"
            image_path.write_bytes(base64.b64decode(encoded))
            emit(
                {
                    "status": "completed",
                    "image_path": str(image_path),
                    "notes": [
                        f"generated with {os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-2')}",
                        f"quality={os.getenv('OPENAI_IMAGE_QUALITY', 'high')}",
                    ],
                }
            )

        if operation == "evaluate":
            reference = Path(request["reference_image"]).expanduser().resolve()
            parent = Path(request["parent_image"]).expanduser().resolve()
            candidate = Path(request["candidate_image"]).expanduser().resolve()
            rubric = {
                "goal": request.get("goal"),
                "anchors": request.get("anchors", []),
                "preserve": request.get("preserve", []),
                "avoid": request.get("avoid", []),
            }
            instruction = (
                "Evaluate the candidate image against the reference, the current parent, and the rubric. "
                "Return JSON only. Use numbers from 0 to 1 for subject_retention, anchor_retention, "
                "environment_match, aesthetic_quality, composition_stability, and drift_penalty. "
                "drift_penalty is 0 when there is no harmful drift and 1 when drift is severe. "
                "Also include a short notes array. Do not reward merely adding detail; reward the requested semantic improvement.\n"
                + json.dumps(rubric, ensure_ascii=False)
            )
            response = client.responses.create(
                model=os.getenv("OPENAI_EVALUATOR_MODEL", "gpt-5.6-luna"),
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": instruction},
                            {"type": "input_text", "text": "Reference image:"},
                            {"type": "input_image", "image_url": data_url(reference), "detail": "high"},
                            {"type": "input_text", "text": "Current parent image:"},
                            {"type": "input_image", "image_url": data_url(parent), "detail": "high"},
                            {"type": "input_text", "text": "Candidate image:"},
                            {"type": "input_image", "image_url": data_url(candidate), "detail": "high"},
                        ],
                    }
                ],
            )
            value = parse_json_object(response.output_text)
            metrics = value.get("metrics", value)
            notes = value.get("notes", [])
            emit({"status": "completed", "metrics": metrics, "notes": notes})

        emit({"status": "error", "error": f"unsupported operation: {operation}"}, exit_code=2)
    except RateLimitError as exc:
        emit(
            {"status": "rate_limited", "error": str(exc), "retry_after": retry_after(exc)},
            exit_code=75,
        )
    except APIStatusError as exc:
        if getattr(exc, "status_code", None) == 429:
            emit(
                {"status": "rate_limited", "error": str(exc), "retry_after": retry_after(exc)},
                exit_code=75,
            )
        emit({"status": "error", "error": str(exc)}, exit_code=2)
    except Exception as exc:
        emit({"status": "error", "error": f"{type(exc).__name__}: {exc}"}, exit_code=2)


if __name__ == "__main__":
    main()
