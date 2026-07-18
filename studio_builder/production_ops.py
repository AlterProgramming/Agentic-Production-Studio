from __future__ import annotations

import json
import math
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

from PIL import Image

from .core import BuilderError, Context, OperationRegistry, canonical_json, normalize_rel, operation_id, sha256_bytes


def _rgba(value: Any, name: str) -> tuple[int, int, int, int]:
    if isinstance(value, str):
        raw = value.removeprefix("#")
        if len(raw) in {6, 8}:
            try:
                parts = tuple(int(raw[index:index + 2], 16) for index in range(0, len(raw), 2))
            except ValueError as exc:
                raise BuilderError(f"{name} is not a valid hex color") from exc
            return (*parts, 255) if len(parts) == 3 else parts  # type: ignore[return-value]
    if isinstance(value, (list, tuple)) and len(value) in {3, 4} and all(isinstance(item, int) and 0 <= item <= 255 for item in value):
        return (*value, 255) if len(value) == 3 else tuple(value)  # type: ignore[return-value]
    raise BuilderError(f"{name} must be #RRGGBB, #RRGGBBAA, RGB, or RGBA")


def _read_image(ctx: Context, path: str, oid: str) -> Image.Image:
    value = ctx.state.read(path)
    if value is None:
        raise BuilderError(f"Operation {oid!r} source does not exist: {path}")
    try:
        with Image.open(BytesIO(value)) as opened:
            return opened.convert("RGBA")
    except Exception as exc:
        raise BuilderError(f"Operation {oid!r} source is not a readable image: {path}") from exc


def _write_png(ctx: Context, target: str, image: Image.Image, oid: str, overwrite: bool) -> None:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    after = buffer.getvalue()
    before = ctx.state.read(target)
    if before == after:
        return
    if before is not None and not overwrite:
        raise BuilderError(f"Operation {oid!r} refuses to overwrite existing file: {target}")
    ctx.state.write(target, after)


def palette_enforce(ctx: Context, operation: dict[str, Any]) -> list[str]:
    oid = operation_id(operation)
    source = normalize_rel(operation.get("source"))
    target = ctx.target(operation.get("target"), oid)
    source_value = ctx.state.read(source)
    if source_value is None:
        raise BuilderError(f"Operation {oid!r} source does not exist: {source}")
    expected_sha = operation.get("expect_source_sha256")
    if expected_sha is not None and sha256_bytes(source_value) != expected_sha:
        raise BuilderError(f"Operation {oid!r} source checksum mismatch: {source}")
    palette_raw = operation.get("palette")
    if not isinstance(palette_raw, list) or not palette_raw:
        raise BuilderError(f"Operation {oid!r} requires a non-empty palette")
    palette = [_rgba(item, f"Operation {oid!r} palette entry") for item in palette_raw]
    threshold = operation.get("transparent_threshold", 0)
    if not isinstance(threshold, int) or not 0 <= threshold <= 255:
        raise BuilderError(f"Operation {oid!r} transparent_threshold must be 0..255")
    if operation.get("dither", False):
        raise BuilderError(f"Operation {oid!r} does not support dithering; deterministic nearest-color mode only")
    preserve_alpha = bool(operation.get("preserve_alpha", True))
    image = _read_image(ctx, source, oid)
    output = Image.new("RGBA", image.size)
    out_pixels = []
    for red, green, blue, alpha in image.get_flattened_data():
        if alpha <= threshold:
            out_pixels.append((0, 0, 0, 0))
            continue
        match = min(
            palette,
            key=lambda item: (red - item[0]) ** 2 + (green - item[1]) ** 2 + (blue - item[2]) ** 2 + (alpha - item[3]) ** 2 * 0.1,
        )
        out_pixels.append((match[0], match[1], match[2], alpha if preserve_alpha else match[3]))
    output.putdata(out_pixels)
    _write_png(ctx, target, output, oid, bool(operation.get("overwrite", False)))
    return [target]


def contact_sheet(ctx: Context, operation: dict[str, Any]) -> list[str]:
    oid = operation_id(operation)
    raw_sources = operation.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise BuilderError(f"Operation {oid!r} requires sources")
    sources = [normalize_rel(path) for path in raw_sources]
    target = ctx.target(operation.get("target"), oid)
    columns = operation.get("columns", len(sources))
    scale = operation.get("scale", 1)
    padding = operation.get("padding", 0)
    if not isinstance(columns, int) or columns <= 0 or not isinstance(scale, int) or scale <= 0 or not isinstance(padding, int) or padding < 0:
        raise BuilderError(f"Operation {oid!r} requires positive columns/scale and non-negative padding")
    background = _rgba(operation.get("background", [0, 0, 0, 0]), f"Operation {oid!r} background")
    images = [_read_image(ctx, path, oid) for path in sources]
    if operation.get("require_equal_size", False) and len({image.size for image in images}) != 1:
        raise BuilderError(f"Operation {oid!r} requires equal-size images")
    cell_width = max(image.width for image in images) * scale
    cell_height = max(image.height for image in images) * scale
    rows = math.ceil(len(images) / columns)
    width = columns * cell_width + (columns + 1) * padding
    height = rows * cell_height + (rows + 1) * padding
    sheet = Image.new("RGBA", (width, height), background)
    for index, image in enumerate(images):
        rendered = image.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
        column, row = index % columns, index // columns
        x = padding + column * cell_width + (cell_width - rendered.width) // 2
        y = padding + row * cell_height + (cell_height - rendered.height) // 2
        sheet.alpha_composite(rendered, dest=(x, y))
    _write_png(ctx, target, sheet, oid, bool(operation.get("overwrite", False)))
    return [target]


def _godot_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def godot_spriteframes_compile(ctx: Context, operation: dict[str, Any]) -> list[str]:
    oid = operation_id(operation)
    raw_frames = operation.get("frame_paths")
    if not isinstance(raw_frames, list) or not raw_frames:
        raise BuilderError(f"Operation {oid!r} requires frame_paths")
    frames = [normalize_rel(path) for path in raw_frames]
    for frame in frames:
        value = ctx.state.read(frame)
        if value is None:
            raise BuilderError(f"Operation {oid!r} frame does not exist: {frame}")
        try:
            with Image.open(BytesIO(value)) as image:
                image.verify()
        except Exception as exc:
            raise BuilderError(f"Operation {oid!r} frame is not a readable image: {frame}") from exc
    target = ctx.target(operation.get("target"), oid)
    animation_name = operation.get("animation_name")
    fps = operation.get("fps")
    loop = operation.get("loop")
    if not isinstance(animation_name, str) or not animation_name.strip() or not isinstance(fps, (int, float)) or fps <= 0 or not isinstance(loop, bool):
        raise BuilderError(f"Operation {oid!r} requires animation_name, positive fps, and boolean loop")
    resource_paths = operation.get("resource_paths")
    if resource_paths is None:
        resource_paths = [f"res://{path}" for path in frames]
    if not isinstance(resource_paths, list) or len(resource_paths) != len(frames) or not all(isinstance(path, str) and path for path in resource_paths):
        raise BuilderError(f"Operation {oid!r} resource_paths must match frame_paths")
    lines = [f'[gd_resource type="SpriteFrames" load_steps={len(frames) + 1} format=3]', ""]
    for index, resource_path in enumerate(resource_paths, start=1):
        lines.append(f'[ext_resource type="Texture2D" path={_godot_string(resource_path)} id="{index}"]')
    lines.extend(["", "[resource]", "animations = [{", '"frames": ['])
    for index in range(1, len(frames) + 1):
        suffix = "," if index < len(frames) else ""
        lines.append(f'{{"duration": 1.0, "texture": ExtResource("{index}")}}{suffix}')
    lines.extend([
        "],",
        f'"loop": {str(loop).lower()},',
        f'"name": &{_godot_string(animation_name)},',
        f'"speed": {float(fps):g}',
        "}]",
        "",
    ])
    content = "\n".join(lines).encode("utf-8")
    before = ctx.state.read(target)
    if before != content:
        if before is not None and not operation.get("overwrite", False):
            raise BuilderError(f"Operation {oid!r} refuses to overwrite existing file: {target}")
        ctx.state.write(target, content)
    touched = [target]
    metadata_target = operation.get("metadata_target")
    if metadata_target is not None:
        metadata_path = ctx.target(metadata_target, oid)
        metadata = {
            "schema_version": "1.0",
            "animation_name": animation_name,
            "fps": float(fps),
            "loop": loop,
            "frame_paths": frames,
            "resource_paths": resource_paths,
            "anchor": operation.get("anchor"),
            "events": operation.get("events", []),
        }
        metadata_bytes = canonical_json(metadata)
        metadata_before = ctx.state.read(metadata_path)
        if metadata_before != metadata_bytes:
            if metadata_before is not None and not operation.get("overwrite", False):
                raise BuilderError(f"Operation {oid!r} refuses to overwrite existing file: {metadata_path}")
            ctx.state.write(metadata_path, metadata_bytes)
        touched.append(metadata_path)
    return touched


def package_zip(ctx: Context, operation: dict[str, Any]) -> list[str]:
    oid = operation_id(operation)
    raw_sources = operation.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise BuilderError(f"Operation {oid!r} requires sources")
    sources = sorted({normalize_rel(path) for path in raw_sources})
    target = ctx.target(operation.get("target"), oid)
    prefix = operation.get("prefix", "")
    if not isinstance(prefix, str):
        raise BuilderError(f"Operation {oid!r} prefix must be a string")
    prefix_path = PurePosixPath(prefix)
    if prefix_path.is_absolute() or ".." in prefix_path.parts:
        raise BuilderError(f"Operation {oid!r} prefix escapes package root")
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sources:
            value = ctx.state.read(source)
            if value is None:
                raise BuilderError(f"Operation {oid!r} source does not exist: {source}")
            arcname = (prefix_path / PurePosixPath(source)).as_posix()
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value)
    after = buffer.getvalue()
    before = ctx.state.read(target)
    if before != after:
        if before is not None and not operation.get("overwrite", False):
            raise BuilderError(f"Operation {oid!r} refuses to overwrite existing file: {target}")
        ctx.state.write(target, after)
    return [target]


def register_production_operations(registry: OperationRegistry) -> None:
    registry.register("palette_enforce", palette_enforce)
    registry.register("contact_sheet", contact_sheet)
    registry.register("godot_spriteframes_compile", godot_spriteframes_compile)
    registry.register("package_zip", package_zip)
