from __future__ import annotations

import argparse
from pathlib import Path

from objectforge.smooth_preview import contact_sheet, render_glb_smooth


LANGUAGES = (
    ("field_service", "Field Service"),
    ("precision_lab", "Precision Lab"),
)
OBJECTS = (
    ("service_hub", "Service Hub"),
    ("work_emitter", "Work Emitter"),
    ("protected_carrier", "Protected Carrier"),
    ("instrument_caddy", "Instrument Caddy"),
    ("power_module", "Power Module"),
    ("analysis_module", "Analysis Module"),
)


def render_scope4(input_root: Path, output_root: Path) -> dict[str, str]:
    output_root.mkdir(parents=True, exist_ok=True)
    system_images: list[tuple[Path, str]] = []
    all_members: list[tuple[Path, str]] = []
    for language_id, language_label in LANGUAGES:
        system_glb = input_root / language_id / "system" / "system.glb"
        system_image = output_root / f"{language_id}-system.png"
        render_glb_smooth(
            system_glb,
            system_image,
            elev=24,
            azim=-38,
            title=f"{language_label} · Modular Observation and Service Cell",
            size=(1180, 760),
            supersample=1,
        )
        system_images.append((system_image, language_label))

        member_images: list[tuple[Path, str]] = []
        for object_id, object_label in OBJECTS:
            glb = input_root / language_id / "objects" / object_id / "object" / "object.glb"
            image = output_root / f"{language_id}-{object_id}.png"
            pose = {"AccessPivot": ("x", -78.0)} if object_id == "protected_carrier" else None
            render_glb_smooth(
                glb,
                image,
                elev=24,
                azim=-42,
                title=f"{language_label} · {object_label}",
                pose=pose,
                size=(760, 580),
                supersample=1,
            )
            member_images.append((image, object_label))
            all_members.append((image, f"{language_label} · {object_label}"))
        contact_sheet(member_images, output_root / f"{language_id}-members.png", columns=3)

    contact_sheet(system_images, output_root / "scope4-system-comparison.png", columns=2)
    contact_sheet(all_members, output_root / "scope4-all-members.png", columns=3)
    for object_id, object_label in OBJECTS:
        contact_sheet(
            [
                (output_root / f"{language_id}-{object_id}.png", language_label)
                for language_id, language_label in LANGUAGES
            ],
            output_root / f"pair-{object_id}.png",
            columns=2,
        )
    return {
        "system_comparison": (output_root / "scope4-system-comparison.png").as_posix(),
        "all_members": (output_root / "scope4-all-members.png").as_posix(),
        "field_service_members": (output_root / "field_service-members.png").as_posix(),
        "precision_lab_members": (output_root / "precision_lab-members.png").as_posix(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Render ObjectForge Scope 4 retained-system previews.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for key, value in render_scope4(args.input, args.output).items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
