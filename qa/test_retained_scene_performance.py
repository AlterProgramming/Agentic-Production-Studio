from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tools.retained_scene_performance import CharacterPerformance, verify_receipt


def test_characters_move_without_camera_motion():
    a0 = CharacterPerformance.matrix_for_node("Characters/Character_A/Hand_R", 0.0)
    a1 = CharacterPerformance.matrix_for_node("Characters/Character_A/Hand_R", 7.5)
    b0 = CharacterPerformance.matrix_for_node("Characters/Character_B/Hand_L", 0.0)
    b1 = CharacterPerformance.matrix_for_node("Characters/Character_B/Hand_L", 4.5)
    assert not np.allclose(a0, a1)
    assert not np.allclose(b0, b1)


def test_environment_nodes_are_not_animated_by_character_performance():
    assert np.allclose(CharacterPerformance.matrix_for_node("Environment/Floor", 0.0), np.eye(4))
    assert np.allclose(CharacterPerformance.matrix_for_node("Environment/Floor", 8.0), np.eye(4))


def test_performance_contains_action_and_reaction():
    ids = [beat.beat_id for beat in CharacterPerformance.beats]
    assert "b_advance" in ids
    assert "b_gesture" in ids
    assert "a_reaction" in ids
    assert ids[-1] == "shared_settle"


def test_contract_measures_node_displacement():
    contract = CharacterPerformance.contract()
    assert contract["acceptance"]["independent_character_motion"] is True
    assert contract["acceptance"]["camera_is_not_only_motion_source"] is True
    assert len(contract["tracked_node_motion_m"]) == 4


def test_receipt_rejects_camera_only_reel():
    receipt = {
        "acceptance": {
            "characters_move_independently": False,
            "performance_has_temporal_change": True,
            "beat_count": 1,
        },
        "measured_node_motion_m": {},
    }
    errors = verify_receipt(receipt)
    assert errors
    assert any("characters_move_independently" in error for error in errors)


def test_receipt_accepts_measured_performance():
    receipt = {
        "acceptance": {
            "characters_move_independently": True,
            "performance_has_temporal_change": True,
            "beat_count": 5,
        },
        "measured_node_motion_m": {
            "Characters/Character_A/Hand_R": 0.87,
            "Characters/Character_A/Head": 0.13,
            "Characters/Character_B/Hand_L": 1.21,
            "Characters/Character_B/Head": 0.08,
        },
    }
    assert verify_receipt(receipt) == []


def test_emit_contract_cli_shape(tmp_path: Path):
    output = tmp_path / "contract.json"
    output.write_text(json.dumps(CharacterPerformance.contract(), indent=2))
    payload = json.loads(output.read_text())
    assert payload["capability_id"] == "AvatarForge.character_performance.v1"
    assert payload["duration_s"] == 13.0
    assert payload["acceptance"]["beat_count"] >= 5
