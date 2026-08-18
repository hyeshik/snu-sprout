import argparse
from datetime import date
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_FAMILY = "SNUSprout"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a distribution ZIP from built SNU Sprout OTF files."
    )
    parser.add_argument(
        "--input-dir",
        default="instance_otf",
        help="Directory containing built SNU Sprout OTF files",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Directory where the distribution ZIP will be written",
    )
    parser.add_argument(
        "--zip-name",
        help="Optional ZIP filename; defaults to SNUSprout-otf-YYYYMMDD.zip",
    )
    parser.add_argument(
        "--family-name",
        default=DEFAULT_FAMILY,
        help="Font family prefix used to select OTFs for packaging",
    )
    parser.add_argument(
        "--include-readme",
        action="store_true",
        help="Include README.md at the root of the ZIP",
    )
    return parser


def find_fonts(input_dir: Path, family_name: str) -> list[Path]:
    fonts = sorted(path for path in input_dir.glob(f"{family_name}-*.otf") if path.is_file())
    if not fonts:
        raise FileNotFoundError(
            f"No built OTFs matching {family_name}-*.otf were found in {input_dir}"
        )
    return fonts


def output_zip_path(output_dir: Path, zip_name: str | None, family_name: str) -> Path:
    if zip_name:
        return output_dir / zip_name
    stamp = date.today().strftime("%Y%m%d")
    return output_dir / f"{family_name}-otf-{stamp}.zip"


def main() -> None:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fonts = find_fonts(input_dir, args.family_name)
    zip_path = output_zip_path(output_dir, args.zip_name, args.family_name)

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for font_path in fonts:
            archive.write(font_path, arcname=font_path.name)
            print(f"Added {font_path.name}")
        if args.include_readme:
            readme_path = Path("README.md")
            if not readme_path.is_file():
                raise FileNotFoundError("README.md was requested but is missing")
            archive.write(readme_path, arcname="README.md")
            print("Added README.md")

    print(f"Wrote {zip_path}")


if __name__ == "__main__":
    main()
