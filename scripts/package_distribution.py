#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FAMILY_PREFIX = "SNUSprout"
STYLE_NAMES = (
    "Thin",
    "ThinItalic",
    "Light",
    "LightItalic",
    "Regular",
    "RegularItalic",
    "Medium",
    "MediumItalic",
    "SemiBold",
    "SemiBoldItalic",
    "Bold",
    "BoldItalic",
    "ExtraBold",
    "ExtraBoldItalic",
    "Black",
    "BlackItalic",
)
EXPECTED_OTF_FILENAMES = tuple(
    f"{FAMILY_PREFIX}-{style}.otf" for style in STYLE_NAMES
)
LICENSE_ENTRIES = (
    ("LICENSE", "LICENSE.txt"),
    ("licenses/LINESeed.txt", "LICENSE-LINESeed.txt"),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create the flat SNU Sprout distribution ZIP."
    )
    parser.add_argument("--input-dir", default="instance_otf")
    parser.add_argument("--output", default="dist/SNUSprout-0.9.3.zip")
    parser.add_argument("--project-root", default=str(PROJECT_ROOT))
    return parser


def find_expected_otfs(input_dir: Path) -> list[Path]:
    paths = [input_dir / filename for filename in EXPECTED_OTF_FILENAMES]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing expected OTF file(s): " + ", ".join(missing))
    return paths


def find_license_files(project_root: Path) -> list[tuple[Path, str]]:
    entries = [(project_root / source, archive_name) for source, archive_name in LICENSE_ENTRIES]
    missing = [str(path) for path, _ in entries if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing license file(s): " + ", ".join(missing))
    return entries


def expected_archive_entries() -> list[str]:
    return list(EXPECTED_OTF_FILENAMES) + [name for _, name in LICENSE_ENTRIES]


def write_distribution(input_dir: Path, output: Path, project_root: Path) -> None:
    fonts = find_expected_otfs(input_dir)
    licenses = find_license_files(project_root)
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for font_path in fonts:
            archive.write(font_path, arcname=font_path.name)
        for license_path, archive_name in licenses:
            archive.write(license_path, arcname=archive_name)

    with ZipFile(output) as archive:
        entries = archive.namelist()
    expected = expected_archive_entries()
    if entries != expected:
        raise RuntimeError(f"Unexpected distribution layout: {entries}")
    print(f"Wrote {output}")


def resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root / path


def main() -> None:
    args = build_parser().parse_args()
    project_root = Path(args.project_root).resolve()
    write_distribution(
        resolve_path(project_root, args.input_dir),
        resolve_path(project_root, args.output),
        project_root,
    )


if __name__ == "__main__":
    main()
