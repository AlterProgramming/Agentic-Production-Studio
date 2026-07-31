from __future__ import annotations

import argparse
from pathlib import Path

from objectforge.smooth_preview import contact_sheet, render_glb_smooth


BRIEFS = (
    ("directional-energy", "Directional Energy"),
    ("protected-transport", "Protected Transport"),
    ("elevated-service", "Elevated Service"),
    ("visible-organization", "Visible Organization"),
)
LANGUAGES = (
    ("field_service", "Field Service"),
    ("precision_lab", "Precision Lab"),
)


def render_scope3(input_root: Path, output_root: Path) -> dict[str, str]:
    output_root.mkdir(parents=True, exist_ok=True)
    all_images: list[tuple[Path, str]] = []
    for language_id, language_label in LANGUAGES:
        family: list[tuple[Path, str]] = []
        for brief_id, brief_label in BRIEFS:
            glb = input_root / language_id / brief_id / "object" / "object.glb"
            image = output_root / f"{language_id}-{brief_id}.png"
            pose = {"AccessPivot": ("x", -82.0)} if brief_id == "protected-transport" else None
            render_glb_smooth(
                glb,
                image,
                elev=24,
                azim=-42,
                title=f"{language_label} · {brief_label}",
                pose=pose,
                size=(820, 650),
                supersample=1,
            )
            family.append((image, brief_label))
            all_images.append((image, f"{language_label} · {brief_label}"))
        contact_sheet(family, output_root / f"{language_id}-family.png", columns=2)
    contact_sheet(all_images, output_root / "scope3-all-assets.png", columns=2)
    for brief_id, brief_label in BRIEFS:
        contact_sheet(
            [
                (output_root / f"{language_id}-{brief_id}.png", language_label)
                for language_id, language_label in LANGUAGES
            ],
            output_root / f"pair-{brief_id}.png",
            columns=2,
        )
    return {
        "all_assets": (output_root / "scope3-all-assets.png").as_posix(),
        "field_service_family": (output_root / "field_service-family.png").as_posix(),
        "precision_lab_family": (output_root / "precision_lab-family.png").as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render ObjectForge Scope 3 retained-model previews.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for key, value in render_scope3(args.input, args.output).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
