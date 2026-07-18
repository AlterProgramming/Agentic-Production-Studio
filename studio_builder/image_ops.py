from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from .core import BuilderError, Context, OperationRegistry, normalize_rel, operation_id, sha256_bytes
from .production_ops import register_production_operations


def _point(value: Any, name: str) -> tuple[int, int]:
    if not isinstance(value, dict) or not isinstance(value.get("x"), int) or not isinstance(value.get("y"), int):
        raise BuilderError(f"image_normalize requires integer {name}.x and {name}.y")
    return value["x"], value["y"]


def image_normalize(ctx: Context, operation: dict[str, Any]) -> list[str]:
    """Place an RGBA source on an exact transparent canvas using explicit anchors."""
    oid = operation_id(operation)
    source = normalize_rel(operation.get("source"))
    target = ctx.target(operation.get("target"), oid)
    canvas = operation.get("canvas")
    if not isinstance(canvas, dict) or not isinstance(canvas.get("width"), int) or not isinstance(canvas.get("height"), int):
        raise BuilderError(f"Operation {oid!r} requires integer canvas width and height")
    width, height = canvas["width"], canvas["height"]
    if width <= 0 or height <= 0:
        raise BuilderError(f"Operation {oid!r} canvas dimensions must be positive")
    source_anchor = _point(operation.get("source_anchor"), "source_anchor")
    target_anchor = _point(operation.get("target_anchor"), "target_anchor")
    source_value = ctx.state.read(source)
    if source_value is None:
        raise BuilderError(f"Operation {oid!r} source does not exist: {source}")
    expected_sha = operation.get("expect_source_sha256")
    actual_sha = sha256_bytes(source_value)
    if expected_sha is not None and actual_sha != expected_sha:
        raise BuilderError(f"Operation {oid!r} source checksum mismatch for {source}: {actual_sha} != {expected_sha}")
    try:
        with Image.open(BytesIO(source_value)) as opened:
            image = opened.convert("RGBA")
    except Exception as exc:
        raise BuilderError(f"Operation {oid!r} source is not a readable image: {source}") from exc
    x = target_anchor[0] - source_anchor[0]
    y = target_anchor[1] - source_anchor[1]
    if not operation.get("allow_crop", False):
        if x < 0 or y < 0 or x + image.width > width or y + image.height > height:
            raise BuilderError(f"Operation {oid!r} would crop source {image.size} at ({x}, {y}) on canvas {(width, height)}")
    output = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    output.alpha_composite(image, dest=(x, y))
    buffer = BytesIO()
    output.save(buffer, format="PNG", optimize=False, compress_level=9)
    after = buffer.getvalue()
    before = ctx.state.read(target)
    if before == after:
        return [target]
    if before is not None and not operation.get("overwrite", False):
        raise BuilderError(f"Operation {oid!r} refuses to overwrite existing file: {target}")
    ctx.state.write(target, after)
    return [target]


def register_image_operations(registry: OperationRegistry) -> None:
    registry.register("image_normalize", image_normalize)
    register_production_operations(registry)
