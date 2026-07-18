from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from studio_builder import BuilderError, StudioBuilder


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def base_plan(operations: list[dict], *, postconditions: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1.0",
        "plan_id": "test-plan",
        "allowed_paths": ["work/**"],
        "preconditions": [],
        "operations": operations,
        "postconditions": postconditions or [],
    }


def test_preview_is_non_mutating_and_shows_exact_diff(tmp_path: Path) -> None:
    target = tmp_path / "work" / "brief.md"
    target.parent.mkdir()
    target.write_text("status: draft\n", encoding="utf-8")
    plan = base_plan(
        [
            {
                "id": "lock-brief",
                "type": "replace_text",
                "path": "work/brief.md",
                "old": "status: draft",
                "new": "status: locked",
                "expected_count": 1,
            }
        ]
    )
    report = StudioBuilder(tmp_path).preview(plan)
    assert target.read_text(encoding="utf-8") == "status: draft\n"
    assert report["summary"]["changed_files"] == 1
    assert "-status: draft" in report["changes"][0]["diff"]
    assert "+status: locked" in report["changes"][0]["diff"]


def test_apply_creates_receipt_and_verify_detects_drift(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("canonical", encoding="utf-8")
    plan = base_plan(
        [{"id": "copy", "type": "copy_file", "source": "source.txt", "target": "work/runtime.txt"}],
        postconditions=[{"id": "runtime-created", "type": "text_contains", "path": "work/runtime.txt", "value": "canonical"}],
    )
    builder = StudioBuilder(tmp_path)
    receipt = builder.apply(plan)
    receipt_path = tmp_path / receipt["receipt_path"]
    assert receipt_path.is_file()
    assert builder.verify_receipt(receipt)["status"] == "PASS"
    (tmp_path / "work" / "runtime.txt").write_text("drifted", encoding="utf-8")
    assert builder.verify_receipt(receipt)["status"] == "FAIL"


def test_json_patch_rejects_stale_expected_value(tmp_path: Path) -> None:
    target = tmp_path / "work" / "brief.json"
    target.parent.mkdir()
    write_json(target, {"status": "review"})
    plan = base_plan(
        [
            {
                "id": "lock",
                "type": "json_patch",
                "path": "work/brief.json",
                "changes": [{"pointer": "/status", "expect": "draft", "value": "locked"}],
            }
        ]
    )
    with pytest.raises(BuilderError, match="stale JSON expectation"):
        StudioBuilder(tmp_path).preview(plan)
    assert json.loads(target.read_text(encoding="utf-8"))["status"] == "review"


def test_path_escape_and_disallowed_target_are_rejected(tmp_path: Path) -> None:
    escape_plan = base_plan([{"id": "escape", "type": "write_text", "path": "../outside.txt", "content": "x"}])
    with pytest.raises(BuilderError, match="escapes workspace"):
        StudioBuilder(tmp_path).preview(escape_plan)
    disallowed_plan = base_plan([{"id": "wrong-area", "type": "write_text", "path": "other/file.txt", "content": "x"}])
    with pytest.raises(BuilderError, match="disallowed path"):
        StudioBuilder(tmp_path).preview(disallowed_plan)


def test_failed_postcondition_prevents_all_writes(tmp_path: Path) -> None:
    plan = base_plan(
        [
            {"id": "one", "type": "write_text", "path": "work/one.txt", "content": "one"},
            {"id": "two", "type": "write_text", "path": "work/two.txt", "content": "two"},
        ],
        postconditions=[{"id": "impossible", "type": "text_contains", "path": "work/two.txt", "value": "three"}],
    )
    with pytest.raises(BuilderError, match="Condition failure"):
        StudioBuilder(tmp_path).apply(plan)
    assert not (tmp_path / "work" / "one.txt").exists()
    assert not (tmp_path / "work" / "two.txt").exists()


def test_delete_requires_exact_checksum(tmp_path: Path) -> None:
    target = tmp_path / "work" / "obsolete.txt"
    target.parent.mkdir()
    target.write_text("obsolete", encoding="utf-8")
    wrong = "0" * 64
    wrong_plan = base_plan([{"id": "delete", "type": "delete_file", "path": "work/obsolete.txt", "expect_sha256": wrong}])
    with pytest.raises(BuilderError, match="deletion checksum mismatch"):
        StudioBuilder(tmp_path).preview(wrong_plan)
    correct = hashlib.sha256(b"obsolete").hexdigest()
    receipt = StudioBuilder(tmp_path).apply(
        base_plan([{"id": "delete", "type": "delete_file", "path": "work/obsolete.txt", "expect_sha256": correct}])
    )
    assert not target.exists()
    assert receipt["changes"][0]["action"] == "delete"


def test_image_normalize_places_source_anchor_exactly(tmp_path: Path) -> None:
    from PIL import Image

    source = tmp_path / "source.png"
    image = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    image.putpixel((1, 1), (0, 255, 0, 255))
    image.save(source)
    plan = base_plan(
        [
            {
                "id": "normalize",
                "type": "image_normalize",
                "source": "source.png",
                "target": "work/normalized.png",
                "canvas": {"width": 6, "height": 6},
                "source_anchor": {"x": 1, "y": 1},
                "target_anchor": {"x": 3, "y": 4},
            }
        ],
        postconditions=[{"id": "output-exists", "type": "exists", "path": "work/normalized.png", "value": True}],
    )
    receipt = StudioBuilder(tmp_path).apply(plan)
    with Image.open(tmp_path / "work" / "normalized.png") as normalized:
        assert normalized.mode == "RGBA"
        assert normalized.size == (6, 6)
        assert normalized.getpixel((3, 4)) == (0, 255, 0, 255)
        assert normalized.getpixel((0, 0)) == (0, 0, 0, 0)
    assert receipt["changes"][0]["action"] == "create"
