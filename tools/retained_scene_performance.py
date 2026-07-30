#!/usr/bin/env python3
"""Author and verify independent character motion over retained scene nodes.

This module deliberately treats camera movement as supporting coverage, not as
proof of scene motion. Acceptance requires measured displacement of named body
nodes and a sequence of authored performance beats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class CameraPose:
    position: tuple[float, float, float]
    target: tuple[float, float, float]
    fov: float


@dataclass(frozen=True)
class PerformanceBeat:
    beat_id: str
    start_s: float
    end_s: float
    action: str


def _smoothstep(x: float) -> float:
    x = float(np.clip(x, 0.0, 1.0))
    return x * x * (3.0 - 2.0 * x)


def _ramp(t: float, start: float, end: float) -> float:
    if end <= start:
        raise ValueError("ramp end must be after start")
    return _smoothstep((t - start) / (end - start))


def _held(t: float, rise0: float, rise1: float, fall0: float, fall1: float) -> float:
    return float(np.clip(_ramp(t, rise0, rise1) - _ramp(t, fall0, fall1), 0.0, 1.0))


def _T(x=0.0, y=0.0, z=0.0) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:3, 3] = [x, y, z]
    return matrix


def _Rx(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    matrix = np.eye(4)
    matrix[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    return matrix


def _Ry(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    matrix = np.eye(4)
    matrix[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    return matrix


def _Rz(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    matrix = np.eye(4)
    matrix[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    return matrix


def _about(pivot: Iterable[float], rotation: np.ndarray) -> np.ndarray:
    p = np.asarray(tuple(pivot), dtype=float)
    return _T(*p) @ rotation @ _T(*(-p))


def _lerp(a: Iterable[float], b: Iterable[float], t: float) -> np.ndarray:
    start = np.asarray(tuple(a), dtype=float)
    end = np.asarray(tuple(b), dtype=float)
    return start * (1.0 - t) + end * t


class CharacterPerformance:
    capability_id = "AvatarForge.character_performance.v1"
    duration_s = 13.0
    character_a_root = np.asarray([-0.8, 0.0, 0.3])
    character_b_root = np.asarray([1.35, 0.0, -0.1])

    beats = (
        PerformanceBeat("held_attention", 0.0, 2.4, "Both figures breathe and maintain eye contact."),
        PerformanceBeat("b_advance", 2.4, 4.8, "Character B shifts weight and steps toward Character A."),
        PerformanceBeat("b_gesture", 3.2, 6.2, "Character B raises the near arm, turns the head, then lowers the hand."),
        PerformanceBeat("a_reaction", 6.0, 8.5, "Character A yields half a step, lifts the chin, and answers."),
        PerformanceBeat("shared_settle", 8.8, 13.0, "Both figures lower their arms and settle at a changed distance."),
    )

    @classmethod
    def state(cls, t: float) -> dict:
        if not 0.0 <= t <= cls.duration_s:
            raise ValueError(f"time must be within 0..{cls.duration_s}")
        breath_a = 0.014 * math.sin(t * 2.1)
        breath_b = 0.012 * math.sin(t * 1.95 + 0.7)
        b_advance = _ramp(t, 2.45, 4.55)
        b_retreat = _ramp(t, 10.4, 12.4)
        b_gesture = _held(t, 3.15, 4.15, 5.45, 6.35)
        b_head = _held(t, 3.0, 3.8, 5.7, 6.5)
        b_nod = _held(t, 4.05, 4.45, 4.85, 5.25)
        a_yield = _ramp(t, 6.05, 7.35)
        a_recover = _ramp(t, 10.2, 12.5)
        a_gesture = _held(t, 6.65, 7.55, 9.0, 9.95)
        a_head = _held(t, 6.15, 7.05, 9.3, 10.1)
        return {
            "A": {
                "translation": np.asarray([-0.13 * (a_yield - 0.22 * a_recover), breath_a, 0.025 * a_yield]),
                "yaw": math.radians(-2.5 * a_head),
                "lean": math.radians(-2.0 * a_head),
                "head_yaw": math.radians(6.0 + 9.0 * a_head),
                "head_pitch": math.radians(-1.0 - 7.0 * a_head),
                "arm_near": math.radians(43.0 * a_gesture),
                "elbow_near": math.radians(22.0 * a_gesture),
            },
            "B": {
                "translation": np.asarray([-0.20 * (b_advance - 0.34 * b_retreat), breath_b, 0.018 * math.sin(t * 1.1)]),
                "yaw": math.radians(3.5 * b_head),
                "lean": math.radians(-3.2 * b_advance + 1.5 * b_retreat),
                "head_yaw": math.radians(-8.0 - 8.0 * b_head),
                "head_pitch": math.radians(5.0 * b_nod - 1.5),
                "arm_near": math.radians(-52.0 * b_gesture),
                "elbow_near": math.radians(-28.0 * b_gesture),
            },
        }

    @classmethod
    def matrix_for_node(cls, node_name: str, t: float) -> np.ndarray:
        state = cls.state(t)
        if node_name.startswith("Characters/Character_A/"):
            current = state["A"]
            root = _T(*current["translation"]) @ _about(cls.character_a_root, _Ry(current["yaw"]) @ _Rz(current["lean"]))
            part = node_name.rsplit("/", 1)[-1]
            if part in {"Head", "BraidCrown", "FaceNose", "HairCap"}:
                return root @ _about((-0.795, 2.27, 0.32), _Ry(current["head_yaw"]) @ _Rx(current["head_pitch"]))
            if part in {"UpperArm_R", "Forearm_R", "Hand_R"}:
                upper = _about((-0.45, 2.02, 0.23), _Rz(current["arm_near"]))
                if part == "UpperArm_R":
                    return root @ upper
                elbow = (upper @ np.asarray([-0.446, 1.60, 0.24, 1.0]))[:3]
                return root @ _about(elbow, _Rz(current["elbow_near"])) @ upper
            return root
        if node_name.startswith("Characters/Character_B/"):
            current = state["B"]
            root = _T(*current["translation"]) @ _about(cls.character_b_root, _Ry(current["yaw"]) @ _Rz(current["lean"]))
            part = node_name.rsplit("/", 1)[-1]
            if part in {"Head", "Braid", "FaceNose", "HairTop", "BraidSegment_1", "BraidSegment_2", "BraidSegment_3"}:
                return root @ _about((1.347, 2.32, -0.09), _Ry(current["head_yaw"]) @ _Rx(current["head_pitch"]))
            if part in {"UpperArm_L", "Forearm_L", "Hand_L"}:
                upper = _about((0.96, 2.12, -0.24), _Rz(current["arm_near"]))
                if part == "UpperArm_L":
                    return root @ upper
                elbow = (upper @ np.asarray([1.00, 1.67, -0.22, 1.0]))[:3]
                return root @ _about(elbow, _Rz(current["elbow_near"])) @ upper
            return root
        return np.eye(4)

    @classmethod
    def camera(cls, t: float) -> CameraPose:
        if t < 3.2:
            q = _smoothstep(t / 3.2)
            return CameraPose(tuple(_lerp((-0.45, 1.72, 5.55), (0.15, 1.78, 4.72), q)), tuple(_lerp((0.22, 1.80, 0.08), (0.28, 1.86, 0.06), q)), 45.0)
        if t < 6.3:
            q = _smoothstep((t - 3.2) / 3.1)
            return CameraPose(tuple(_lerp((-2.35, 1.78, 2.12), (-1.88, 1.88, 1.35), q)), tuple(_lerp((1.22, 1.93, -0.08), (1.08, 2.02, -0.03), q)), 41.0)
        if t < 9.5:
            q = _smoothstep((t - 6.3) / 3.2)
            return CameraPose(tuple(_lerp((2.55, 1.84, 1.95), (2.10, 1.92, 1.10), q)), tuple(_lerp((-0.82, 1.94, 0.31), (-0.92, 2.04, 0.32), q)), 40.0)
        q = _smoothstep((t - 9.5) / 3.5)
        angle = math.radians(27.0 - 58.0 * q)
        radius = 4.45 - 0.30 * q
        return CameraPose((math.sin(angle) * radius, 2.15 + 0.28 * q, math.cos(angle) * radius), (0.18, 1.66, 0.04), 48.0)

    @classmethod
    def contract(cls) -> dict:
        tracked = (
            "Characters/Character_A/Hand_R",
            "Characters/Character_A/Head",
            "Characters/Character_B/Hand_L",
            "Characters/Character_B/Head",
        )
        displacement = {}
        for node in tracked:
            origin = np.asarray([0.0, 0.0, 0.0, 1.0])
            points = np.asarray([(cls.matrix_for_node(node, float(t)) @ origin)[:3] for t in np.linspace(0.0, cls.duration_s, 80)])
            displacement[node] = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        return {
            "schema_version": "1.0.0",
            "capability_id": cls.capability_id,
            "duration_s": cls.duration_s,
            "beats": [asdict(beat) for beat in cls.beats],
            "tracked_node_motion_m": displacement,
            "acceptance": {
                "beat_count": len(cls.beats),
                "independent_character_motion": all(value > 0.05 for value in displacement.values()),
                "camera_is_not_only_motion_source": any(value > 0.10 for value in displacement.values()),
            },
        }


def verify_receipt(receipt: dict) -> list[str]:
    errors: list[str] = []
    acceptance = receipt.get("acceptance", {})
    if acceptance.get("characters_move_independently") is not True:
        errors.append("characters_move_independently must be measured true")
    if acceptance.get("performance_has_temporal_change") is not True:
        errors.append("performance_has_temporal_change must be measured true")
    if acceptance.get("beat_count", 0) < 4:
        errors.append("at least four authored performance beats are required")
    motion = receipt.get("measured_node_motion_m", {})
    for required in (
        "Characters/Character_A/Hand_R",
        "Characters/Character_A/Head",
        "Characters/Character_B/Hand_L",
        "Characters/Character_B/Head",
    ):
        if float(motion.get(required, 0.0)) <= 0.05:
            errors.append(f"insufficient measured motion for {required}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    emit = sub.add_parser("emit-contract")
    emit.add_argument("output", type=Path)
    verify = sub.add_parser("verify-receipt")
    verify.add_argument("receipt", type=Path)
    args = parser.parse_args()
    if args.command == "emit-contract":
        payload = CharacterPerformance.contract()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n")
        print(args.output)
        return 0
    receipt = json.loads(args.receipt.read_text())
    errors = verify_receipt(receipt)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(hashlib.sha256(args.receipt.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
