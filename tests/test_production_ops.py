from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from studio_builder.core import StudioBuilder


def save_image(path: Path, pixels: list[tuple[int, int, int, int]], size: tuple[int, int]) -> None:
    image = Image.new("RGBA", size)
    image.putdata(pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def test_palette_enforce_uses_nearest_color_and_preserves_alpha(tmp_path: Path) -> None:
    save_image(tmp_path / "source.png", [(250, 10, 10, 128), (10, 10, 240, 255)], (2, 1))
    plan = {
        "schema_version": "1.0",
        "plan_id": "palette",
        "allowed_paths": ["out/**"],
        "operations": [{
            "id": "palette",
            "type": "palette_enforce",
            "source": "source.png",
            "target": "out/palette.png",
            "palette": ["#ff0000", "#0000ff"],
        }],
    }
    StudioBuilder(tmp_path).apply(plan)
    with Image.open(tmp_path / "out/palette.png") as image:
        assert list(image.convert("RGBA").get_flattened_data()) == [(255, 0, 0, 128), (0, 0, 255, 255)]


def test_contact_sheet_is_nearest_neighbor_and_deterministic(tmp_path: Path) -> None:
    save_image(tmp_path / "a.png", [(255, 0, 0, 255)], (1, 1))
    save_image(tmp_path / "b.png", [(0, 0, 255, 255)], (1, 1))
    plan = {
        "schema_version": "1.0",
        "plan_id": "sheet",
        "allowed_paths": ["out/**"],
        "operations": [{
            "id": "sheet",
            "type": "contact_sheet",
            "sources": ["a.png", "b.png"],
            "target": "out/sheet.png",
            "columns": 2,
            "scale": 2,
            "padding": 1,
        }],
    }
    builder = StudioBuilder(tmp_path)
    first = builder.apply(plan)
    with Image.open(tmp_path / "out/sheet.png") as image:
        assert image.size == (7, 4)
        assert image.getpixel((1, 1)) == (255, 0, 0, 255)
        assert image.getpixel((4, 1)) == (0, 0, 255, 255)
    second = builder.preview({**plan, "operations": [{**plan["operations"][0], "overwrite": True}]})
    assert second["summary"]["changed_files"] == 0
    assert first["status"] == "PASS"


def test_godot_spriteframes_compile_writes_resource_and_metadata(tmp_path: Path) -> None:
    for index in range(2):
        save_image(tmp_path / f"frames/f{index}.png", [(index * 255, 0, 0, 255)], (1, 1))
    plan = {
        "schema_version": "1.0",
        "plan_id": "godot",
        "allowed_paths": ["godot/**"],
        "operations": [{
            "id": "godot",
            "type": "godot_spriteframes_compile",
            "frame_paths": ["frames/f0.png", "frames/f1.png"],
            "resource_paths": ["res://frames/f0.png", "res://frames/f1.png"],
            "target": "godot/attack.tres",
            "metadata_target": "godot/attack.events.json",
            "animation_name": "attack",
            "fps": 8,
            "loop": False,
            "anchor": {"x": 8, "y": 14},
            "events": [{"event": "impact", "frame": 1}],
        }],
    }
    StudioBuilder(tmp_path).apply(plan)
    resource = (tmp_path / "godot/attack.tres").read_text()
    assert 'name": &"attack"' in resource
    assert 'speed": 8' in resource
    assert resource.count("ExtResource") == 2
    metadata = json.loads((tmp_path / "godot/attack.events.json").read_text())
    assert metadata["events"] == [{"event": "impact", "frame": 1}]


def test_package_zip_is_sorted_and_byte_reproducible(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("A")
    (tmp_path / "b.txt").write_text("B")
    plan = {
        "schema_version": "1.0",
        "plan_id": "package",
        "allowed_paths": ["out/**"],
        "operations": [{
            "id": "package",
            "type": "package_zip",
            "sources": ["b.txt", "a.txt"],
            "target": "out/package.zip",
            "prefix": "delivery",
        }],
    }
    builder = StudioBuilder(tmp_path)
    builder.apply(plan)
    first = (tmp_path / "out/package.zip").read_bytes()
    preview = builder.preview({**plan, "operations": [{**plan["operations"][0], "overwrite": True}]})
    assert preview["summary"]["changed_files"] == 0
    with zipfile.ZipFile(BytesIO(first)) as archive:
        assert archive.namelist() == ["delivery/a.txt", "delivery/b.txt"]
        assert archive.read("delivery/a.txt") == b"A"
