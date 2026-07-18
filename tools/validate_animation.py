#!/usr/bin/env python3
"""Deterministically validate an integrated frame-animation package."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

STAGES = ("contract", "frames", "delivery")


class Run:
    def __init__(self, root: Path, stage: str):
        self.root, self.stage, self.checks = root.resolve(), stage, []

    def add(self, check_id: str, status: str, message: str, severity="info", **evidence: Any):
        self.checks.append({
            "check_id": check_id, "severity": severity, "status": status,
            "message": message, "evidence": evidence,
        })

    def ok(self, check_id: str, message: str, **evidence: Any):
        self.add(check_id, "PASS", message, **evidence)

    def fail(self, check_id: str, severity: str, message: str, **evidence: Any):
        self.add(check_id, "FAIL", message, severity, **evidence)

    def skip(self, check_id: str, message: str):
        self.add(check_id, "SKIP", message)

    def report(self):
        statuses = {k: sum(c["status"] == k for c in self.checks) for k in ("PASS", "FAIL", "SKIP")}
        failures = {
            s: sum(c["status"] == "FAIL" and c["severity"] == s for c in self.checks)
            for s in ("info", "minor", "major", "blocking")
        }
        return {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "package_root": str(self.root),
            "stage": self.stage,
            "status": "FAIL" if failures["blocking"] or failures["major"] else "PASS",
            "summary": {"checks": statuses, "failures_by_severity": failures},
            "checks": self.checks,
        }


def get(obj: Any, *keys: str):
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def load(run: Run, name: str):
    path = run.root / name
    if not path.is_file():
        run.fail(f"file.{name}.exists", "blocking", f"Missing {name}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("root must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        run.fail(f"file.{name}.parse", "blocking", f"Could not parse {name}: {exc}")
        return None
    run.ok(f"file.{name}.parse", f"Parsed {name}")
    return value


def required(run: Run, label: str, obj: dict | None, names: tuple[str, ...]):
    if obj is None:
        return
    missing = [name for name in names if obj.get(name) in (None, "", [])]
    if missing:
        run.fail(f"{label}.required_fields", "blocking", f"{label} is incomplete", missing=missing)
    else:
        run.ok(f"{label}.required_fields", f"{label} required values are present")


def validate_contract(run: Run, brief, manifest, provenance):
    required(run, "brief", brief, (
        "schema_version", "status", "asset_id", "animation_id", "gameplay_purpose",
        "frame_count", "fps", "loop", "canvas", "anchor", "timing", "palette",
        "background_conditions", "export",
    ))
    required(run, "manifest", manifest, (
        "schema_version", "pipeline_version", "asset_id", "animation_id", "frame_count",
        "fps", "loop", "canvas", "anchor", "frames", "event_frames", "outputs",
    ))
    required(run, "provenance", provenance, ("schema_version", "asset_id", "source", "tools", "rights"))
    if brief is None or manifest is None:
        return

    if brief.get("status") == "locked":
        run.ok("brief.status.locked", "Animation brief is locked")
    else:
        run.fail("brief.status.locked", "blocking", "Animation brief must be locked", actual=brief.get("status"))

    count = brief.get("frame_count")
    if isinstance(count, int) and not isinstance(count, bool) and 4 <= count <= 8:
        run.ok("brief.frame_count.range", "V1 frame count is within 4–8")
    else:
        run.fail("brief.frame_count.range", "blocking", "V1 requires four through eight frames", actual=count)

    fps = brief.get("fps")
    if isinstance(fps, (int, float)) and not isinstance(fps, bool) and fps > 0:
        run.ok("brief.fps.valid", "FPS is valid", fps=fps)
    else:
        run.fail("brief.fps.valid", "blocking", "FPS must be greater than zero", actual=fps)

    width, height = get(brief, "canvas", "width"), get(brief, "canvas", "height")
    if all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in (width, height)):
        run.ok("brief.canvas.valid", "Canvas dimensions are valid", width=width, height=height)
    else:
        run.fail("brief.canvas.valid", "blocking", "Canvas dimensions must be positive integers", width=width, height=height)

    ax, ay = get(brief, "anchor", "x"), get(brief, "anchor", "y")
    anchor_valid = all(isinstance(v, int) and not isinstance(v, bool) for v in (ax, ay))
    anchor_valid = anchor_valid and isinstance(width, int) and isinstance(height, int) and 0 <= ax < width and 0 <= ay < height
    if anchor_valid:
        run.ok("brief.anchor.valid", "Anchor is inside the canvas", x=ax, y=ay)
    else:
        run.fail("brief.anchor.valid", "blocking", "Anchor must be inside the canvas", x=ax, y=ay)

    timing = brief.get("timing") if isinstance(brief.get("timing"), dict) else {}
    bad_timing = {
        name: timing.get(name) for name in ("anticipation", "action", "impact", "peak_effect", "recovery")
        if not isinstance(timing.get(name), int) or not isinstance(count, int) or not 0 <= timing.get(name) < count
    }
    if bad_timing:
        run.fail("brief.timing.valid", "blocking", "Motion-stage frame indexes are invalid", invalid=bad_timing)
    else:
        run.ok("brief.timing.valid", "Motion-stage frame indexes are valid")

    compare = ("asset_id", "animation_id", "frame_count", "fps", "loop", "canvas", "anchor")
    mismatches = {name: {"brief": brief.get(name), "manifest": manifest.get(name)} for name in compare if brief.get(name) != manifest.get(name)}
    if mismatches:
        run.fail("contract.brief_manifest_consistency", "blocking", "Brief and manifest disagree", mismatches=mismatches)
    else:
        run.ok("contract.brief_manifest_consistency", "Brief and manifest agree")

    events = manifest.get("event_frames")
    invalid = []
    if not isinstance(events, list) or not events:
        invalid.append({"reason": "at least one gameplay event is required"})
    else:
        for event in events:
            frame = event.get("frame") if isinstance(event, dict) else None
            if not isinstance(event, dict) or not event.get("event") or not isinstance(frame, int) or not isinstance(count, int) or not 0 <= frame < count:
                invalid.append(event)
    if invalid:
        run.fail("manifest.event_frames.valid", "blocking", "Gameplay event metadata is invalid", invalid=invalid)
    else:
        run.ok("manifest.event_frames.valid", "Gameplay event metadata is valid")


def frame_paths(root: Path, manifest: dict):
    spec = manifest.get("frames") if isinstance(manifest.get("frames"), dict) else {}
    count, pattern = manifest.get("frame_count"), spec.get("pattern", "frame_{index:03d}.png")
    if not isinstance(count, int):
        return []
    try:
        return [root / spec.get("directory", "frames") / pattern.format(index=i) for i in range(count)]
    except (KeyError, ValueError):
        return []


def centroid(image: Image.Image):
    alpha = image.getchannel("A")
    if alpha.getbbox() is None:
        return None
    total = sx = sy = 0
    for y in range(image.height):
        for x in range(image.width):
            a = alpha.getpixel((x, y))
            total, sx, sy = total + a, sx + x * a, sy + y * a
    return None if total == 0 else (sx / total, sy / total)


def validate_frames(run: Run, brief, manifest, config):
    if brief is None or manifest is None:
        run.skip("frames.all", "Frame checks skipped because contract files are invalid")
        return
    paths = frame_paths(run.root, manifest)
    if not paths:
        run.fail("frames.pattern.valid", "blocking", "Frame pattern could not produce expected paths")
        return
    missing = [str(path.relative_to(run.root)) for path in paths if not path.is_file()]
    if missing:
        run.fail("frames.complete", "blocking", "Expected frames are missing", missing=missing)
        return
    run.ok("frames.complete", "All expected frames are present", count=len(paths))

    actual = sorted(paths[0].parent.glob("*.png"))
    extras = [str(path.relative_to(run.root)) for path in actual if path not in paths]
    if extras:
        run.fail("frames.no_extras", "major", "Unexpected PNG frames are present", extras=extras)
    else:
        run.ok("frames.no_extras", "No unexpected PNG frames are present")

    width, height = get(brief, "canvas", "width"), get(brief, "canvas", "height")
    maximum_colors = get(brief, "palette", "maximum_colors")
    allowed_raw = get(brief, "palette", "allowed_rgba")
    try:
        allowed = {tuple(map(int, c)) for c in allowed_raw} if allowed_raw else None
    except (TypeError, ValueError):
        allowed = None
        run.fail("brief.palette.parse", "blocking", "allowed_rgba must contain RGBA arrays")
    limits = config.get("limits", {}) if isinstance(config, dict) else {}
    max_frame = limits.get("max_frame_bytes", 100_000)
    max_sequence = limits.get("max_sequence_bytes", 1_000_000)
    transparent_border = bool(get(config, "alpha", "require_transparent_border"))
    centers, arrays, total_size = [], [], 0

    for index, path in enumerate(paths):
        size = path.stat().st_size
        total_size += size
        if size > max_frame:
            run.fail(f"frame.{index}.size", "major", "Frame exceeds file-size budget", bytes=size, maximum=max_frame)
        try:
            with Image.open(path) as opened:
                fmt, mode = opened.format, opened.mode
                image = opened.convert("RGBA")
                image.load()
        except (OSError, ValueError) as exc:
            run.fail(f"frame.{index}.decode", "blocking", f"Could not decode frame: {exc}")
            continue
        if fmt != "PNG":
            run.fail(f"frame.{index}.png", "blocking", "Frame is not PNG", actual=fmt)
        if mode not in {"RGBA", "LA", "P"}:
            run.fail(f"frame.{index}.alpha_mode", "blocking", "Frame lacks an alpha-capable mode", actual=mode)
        if image.size != (width, height):
            run.fail(f"frame.{index}.dimensions", "blocking", "Frame dimensions do not match brief", actual=list(image.size), expected=[width, height])
        pixels = list(image.get_flattened_data())
        arrays.append(pixels)
        unique = set(pixels)
        if isinstance(maximum_colors, int) and len(unique) > maximum_colors:
            run.fail(f"frame.{index}.color_count", "major", "Frame exceeds palette limit", unique_colors=len(unique), maximum=maximum_colors)
        if allowed is not None:
            violations = sorted(unique - allowed)
            if violations:
                run.fail(f"frame.{index}.palette", "major", "Frame contains unapproved colors", violation_count=len(violations), sample=[list(c) for c in violations[:10]])
        if transparent_border:
            border = [image.getpixel((x, y)) for x in range(image.width) for y in (0, image.height - 1)]
            border += [image.getpixel((x, y)) for y in range(image.height) for x in (0, image.width - 1)]
            opaque = sum(pixel[3] != 0 for pixel in border)
            if opaque:
                run.fail(f"frame.{index}.transparent_border", "major", "Required transparent border is contaminated", opaque_border_pixels=opaque)
        c = centroid(image)
        centers.append(c)
        if c is None:
            run.fail(f"frame.{index}.nonempty", "blocking", "Frame is fully transparent")

    if total_size > max_sequence:
        run.fail("frames.sequence_size", "major", "Sequence exceeds file-size budget", bytes=total_size, maximum=max_sequence)
    else:
        run.ok("frames.sequence_size", "Sequence is within file-size budget", bytes=total_size)

    drift = config.get("drift", {}) if isinstance(config, dict) else {}
    if drift.get("check_alpha_centroid") and centers and all(c is not None for c in centers):
        worst = max(math.dist(centers[0], c) for c in centers)
        maximum = float(drift.get("max_centroid_delta_pixels", 1.0))
        if worst > maximum:
            run.fail("frames.alpha_centroid_drift", "major", "Centroid drift exceeds tolerance", worst_delta=worst, maximum=maximum)
        else:
            run.ok("frames.alpha_centroid_drift", "Centroid drift is within tolerance", worst_delta=worst)
    else:
        run.skip("frames.alpha_centroid_drift", "Centroid drift heuristic is disabled")

    loop_cfg = config.get("loop_seam", {}) if isinstance(config, dict) else {}
    if brief.get("loop") and loop_cfg.get("check_pixel_difference") and len(arrays) >= 2:
        ratio = sum(a != b for a, b in zip(arrays[0], arrays[-1])) / max(1, len(arrays[0]))
        maximum = float(loop_cfg.get("max_changed_pixel_ratio", 0.15))
        if ratio > maximum:
            run.fail("frames.loop_seam.pixel_difference", "major", "Loop seam exceeds tolerance", changed_pixel_ratio=ratio, maximum=maximum)
        else:
            run.ok("frames.loop_seam.pixel_difference", "Loop seam is within tolerance", changed_pixel_ratio=ratio)
    else:
        run.skip("frames.loop_seam.pixel_difference", "Pixel loop-seam heuristic is disabled or animation is one-shot")


def validate_delivery(run: Run, brief, manifest, config):
    if brief is None or manifest is None:
        run.skip("delivery.all", "Delivery checks skipped because contract files are invalid")
        return
    outputs = manifest.get("outputs") if isinstance(manifest.get("outputs"), dict) else {}
    keys = ("preview", "contact_sheet", "godot_spriteframes", "integration_guide")
    missing_keys = [key for key in keys if not outputs.get(key)]
    if missing_keys:
        run.fail("delivery.outputs.declared", "blocking", "Mandatory outputs are not declared", missing=missing_keys)
        return
    missing = [{"output": key, "path": outputs[key]} for key in keys if not (run.root / outputs[key]).is_file()]
    if missing:
        run.fail("delivery.outputs.exist", "blocking", "Mandatory delivery outputs are missing", missing=missing)
    else:
        run.ok("delivery.outputs.exist", "Mandatory delivery outputs exist")
    godot = run.root / outputs["godot_spriteframes"]
    if godot.is_file():
        text = godot.read_text(encoding="utf-8", errors="replace")
        tokens = [str(brief.get("animation_id")), "SpriteFrames"]
        absent = [token for token in tokens if token not in text]
        if absent:
            run.fail("delivery.godot.resource_tokens", "major", "Godot resource lacks expected identifiers", missing=absent)
        else:
            run.ok("delivery.godot.resource_tokens", "Godot resource contains expected identifiers")
    package_zip = run.root.with_suffix(".zip")
    maximum = get(config, "limits", "max_package_bytes") or 5_000_000
    if not package_zip.is_file():
        run.skip("delivery.package_size", "No sibling ZIP found")
    elif package_zip.stat().st_size > maximum:
        run.fail("delivery.package_size", "minor", "Delivery ZIP exceeds budget", bytes=package_zip.stat().st_size, maximum=maximum)
    else:
        run.ok("delivery.package_size", "Delivery ZIP is within budget")


def validate(package_root: Path, stage: str):
    run = Run(package_root, stage)
    if not package_root.is_dir():
        run.fail("package.exists", "blocking", "Package root does not exist")
        return run.report()
    run.ok("package.exists", "Package root exists")
    brief = load(run, "animation-brief.json")
    manifest = load(run, "manifest.json")
    provenance = load(run, "provenance.json")
    config = load(run, "qa-config.json")
    validate_contract(run, brief, manifest, provenance)
    if stage in {"frames", "delivery"}:
        validate_frames(run, brief, manifest, config)
    if stage == "delivery":
        validate_delivery(run, brief, manifest, config)
    return run.report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_root", type=Path)
    parser.add_argument("--stage", choices=STAGES, default="delivery")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fail-on-minor", action="store_true")
    args = parser.parse_args(argv)
    report = validate(args.package_root, args.stage)
    text = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    failures = report["summary"]["failures_by_severity"]
    return int(bool(failures["blocking"] or failures["major"] or (args.fail_on_minor and failures["minor"])))


if __name__ == "__main__":
    raise SystemExit(main())
