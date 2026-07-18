from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_animation import validate  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def make_package(root: Path, *, bad_dimensions: bool = False, missing_frame: bool = False) -> None:
    (root / "frames").mkdir(parents=True)
    (root / "previews").mkdir()
    (root / "godot").mkdir()

    brief = {
        "schema_version": "1.0",
        "status": "locked",
        "asset_id": "storm",
        "animation_id": "storm_attack",
        "gameplay_purpose": "Telegraph and resolve a lightning impact",
        "frame_count": 4,
        "fps": 8,
        "loop": False,
        "canvas": {"width": 16, "height": 16},
        "anchor": {"x": 8, "y": 14},
        "timing": {"anticipation": 0, "action": 1, "impact": 2, "peak_effect": 2, "recovery": 3},
        "palette": {"maximum_colors": 8, "allowed_rgba": []},
        "background_conditions": ["dark", "light"],
        "export": {"native_scale": 1, "preview_scale": 4},
    }
    manifest = {
        "schema_version": "1.0",
        "pipeline_version": "v1",
        "asset_id": "storm",
        "animation_id": "storm_attack",
        "frame_count": 4,
        "fps": 8,
        "loop": False,
        "canvas": {"width": 16, "height": 16},
        "anchor": {"x": 8, "y": 14},
        "frames": {"directory": "frames", "pattern": "storm_attack_{index:03d}.png"},
        "event_frames": [{"event": "impact", "frame": 2}],
        "outputs": {
            "preview": "previews/storm_attack.gif",
            "contact_sheet": "previews/storm_attack_contact-sheet.png",
            "godot_spriteframes": "godot/storm_attack.tres",
            "integration_guide": "integration-guide.md",
        },
    }
    provenance = {
        "schema_version": "1.0",
        "asset_id": "storm",
        "source": {"id": "test-source", "path": "source/storm.png"},
        "tools": [{"name": "test fixture", "version": "1"}],
        "rights": {"status": "internal-test"},
    }
    config = {
        "limits": {"max_frame_bytes": 100000, "max_sequence_bytes": 1000000, "max_package_bytes": 5000000},
        "alpha": {"require_transparent_border": True},
        "drift": {"check_alpha_centroid": False, "max_centroid_delta_pixels": 1},
        "loop_seam": {"check_pixel_difference": False, "max_changed_pixel_ratio": 0.15},
    }
    write_json(root / "animation-brief.json", brief)
    write_json(root / "manifest.json", manifest)
    write_json(root / "provenance.json", provenance)
    write_json(root / "qa-config.json", config)

    for index in range(4):
        if missing_frame and index == 3:
            continue
        size = (15, 16) if bad_dimensions and index == 1 else (16, 16)
        image = Image.new("RGBA", size, (0, 0, 0, 0))
        image.putpixel((8, 8), (255, 255, 255, 255))
        image.save(root / "frames" / f"storm_attack_{index:03d}.png")

    (root / "previews" / "storm_attack.gif").write_bytes(b"GIF89a")
    Image.new("RGBA", (64, 16), (0, 0, 0, 0)).save(root / "previews" / "storm_attack_contact-sheet.png")
    (root / "godot" / "storm_attack.tres").write_text(
        '[gd_resource type="SpriteFrames" format=3]\n# storm_attack\n', encoding="utf-8"
    )
    (root / "integration-guide.md").write_text("# Integration\n", encoding="utf-8")


def failed_ids(report: dict) -> set[str]:
    return {check["check_id"] for check in report["checks"] if check["status"] == "FAIL"}


def test_valid_delivery_package_passes(tmp_path: Path) -> None:
    make_package(tmp_path)
    report = validate(tmp_path, "delivery")
    assert report["status"] == "PASS"
    assert report["summary"]["failures_by_severity"]["blocking"] == 0
    assert report["summary"]["failures_by_severity"]["major"] == 0


def test_missing_frame_is_blocking(tmp_path: Path) -> None:
    make_package(tmp_path, missing_frame=True)
    report = validate(tmp_path, "frames")
    assert report["status"] == "FAIL"
    assert "frames.complete" in failed_ids(report)


def test_bad_dimensions_are_blocking(tmp_path: Path) -> None:
    make_package(tmp_path, bad_dimensions=True)
    report = validate(tmp_path, "frames")
    assert report["status"] == "FAIL"
    assert "frame.1.dimensions" in failed_ids(report)


def test_unlocked_brief_is_blocking(tmp_path: Path) -> None:
    make_package(tmp_path)
    brief_path = tmp_path / "animation-brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["status"] = "draft"
    write_json(brief_path, brief)
    report = validate(tmp_path, "contract")
    assert report["status"] == "FAIL"
    assert "brief.status.locked" in failed_ids(report)
