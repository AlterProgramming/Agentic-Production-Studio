from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "validate_scene.py"
SPEC = importlib.util.spec_from_file_location("mnemonic_validate_scene", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
validate_scene = MODULE.validate_scene

EXAMPLE = Path(__file__).resolve().parents[3] / "benchmarks" / "mnemonic-separation-contract" / "example.scene.json"


class MnemonicSceneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scene = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_example_is_valid(self) -> None:
        self.assertEqual(validate_scene(self.scene), [])

    def test_body_and_artifact_ids_must_be_disjoint(self) -> None:
        mutated = copy.deepcopy(self.scene)
        mutated["layers"]["artifacts"][0]["id"] = "body.subject"
        errors = validate_scene(mutated)
        self.assertTrue(any("must be disjoint" in error for error in errors))

    def test_every_object_requires_provenance(self) -> None:
        mutated = copy.deepcopy(self.scene)
        mutated["layers"]["provenance"].pop()
        errors = validate_scene(mutated)
        self.assertTrue(any("missing provenance" in error for error in errors))

    def test_conflict_must_remain_visible(self) -> None:
        mutated = copy.deepcopy(self.scene)
        mutated["layers"]["hypotheses"] = [mutated["layers"]["hypotheses"][0]]
        errors = validate_scene(mutated)
        self.assertTrue(any("unresolved hypothesis" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
