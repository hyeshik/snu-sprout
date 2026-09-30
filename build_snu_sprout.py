#!/usr/bin/env fontforge -lang=py -script
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import math
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Iterator, NamedTuple

from fontTools.misc.roundTools import otRound
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.scaleUpem import ScalerVisitor
from fontTools.ttLib.tables import otTables


FAMILY_NAME = "SNU Sprout"
POSTSCRIPT_FAMILY_NAME = "SNUSprout"
FILE_FAMILY_NAME = POSTSCRIPT_FAMILY_NAME
VERSION = "0.9.3"
UPSTREAM_COPYRIGHT = "Copyright (c) LY Corporation."
DERIVATIVE_COPYRIGHT = "Copyright (c) 2026 Hyeshik Chang (modifications)."
COPYRIGHT_TEXT = f"{UPSTREAM_COPYRIGHT} {DERIVATIVE_COPYRIGHT}"
LICENSE_DESCRIPTION = "SIL Open Font License, Version 1.1"
LICENSE_URL = "https://openfontlicense.org"
DEFAULT_SOURCE_ZIP_URL = "https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip"
DEFAULT_EN_SOURCE_ZIP_URL = "https://seed.line.me/src/images/fonts/LINE_Seed_Sans_EN.zip"
DEFAULT_DOWNLOAD_DIR = "vendor/downloads"
DEFAULT_SOURCE_DIR = "original"
DEFAULT_OUTPUT_DIR = "instance_otf"
DEFAULT_ITALIC_ANGLE = 10.0
DEFAULT_GUARD_CLEARANCE = 30
DEFAULT_GUARD_BUCKET_SIZE = 5
USE_TYPO_METRICS = 1 << 7
PANOSE_WEIGHT_NO_FIT = 1
INTERPOLATION_REFERENCE_CODEPOINT = 0x49
INTERPOLATION_POINT_DISTANCE_LIMIT = 100.0
INTERPOLATION_BOUNDS_TOLERANCE = 5.0
INTERPOLATION_AREA_TOLERANCE = 2.0
FALLBACK_AREA_SEARCH_STEPS = 3
UNENCODED_NAME_PREFIX = "sprout"
EN_SOURCE_FILES = {
    "Bold": "LINESeedSans_Bd.otf",
    "ExtraBold": "LINESeedSans_XBd.otf",
}
LIGHT_INTERPOLATION_AMOUNT = 0.55
EXTRABOLD_KR_INTERPOLATION_AMOUNT = 1.288
BLACK_KR_INTERPOLATION_AMOUNT = 1.576
HANGUL_X_SCALE = 0.9859268194611982
HANGUL_Y_SCALE = 0.9954128440366973
HANGUL_X_SHIFT = 1.2436670687575373
HANGUL_Y_SHIFT = 3.166552711981929
HANGUL_ADVANCE_SCALE = 0.9928274820687052

SOURCE_FILES = {
    "Thin": "LINESeedKR-Th.otf",
    "Regular": "LINESeedKR-Rg.otf",
    "Bold": "LINESeedKR-Bd.otf",
}


class StyleSpec(NamedTuple):
    style: str
    weight: int
    source_label: str
    lower_label: str | None = None
    upper_label: str | None = None
    interpolation_amount: float | None = None


class InterpolationStats(NamedTuple):
    matched: int
    direct: int
    fallback: int
    missing: int


STYLE_SPECS = (
    StyleSpec("Thin", 100, "Thin"),
    StyleSpec(
        "Light",
        300,
        "Thin",
        "Thin",
        "Regular",
        LIGHT_INTERPOLATION_AMOUNT,
    ),
    StyleSpec("Regular", 400, "Regular"),
    StyleSpec("Medium", 500, "Regular", "Regular", "Bold", 1 / 3),
    StyleSpec("SemiBold", 600, "Regular", "Regular", "Bold", 2 / 3),
    StyleSpec("Bold", 700, "Bold"),
    StyleSpec(
        "ExtraBold",
        800,
        "Bold",
        "Regular",
        "Bold",
        EXTRABOLD_KR_INTERPOLATION_AMOUNT,
    ),
    StyleSpec(
        "Black",
        900,
        "Bold",
        "Regular",
        "Bold",
        BLACK_KR_INTERPOLATION_AMOUNT,
    ),
)


CJK_CODEPOINT_RANGES = (
    (0x1100, 0x11FF),
    (0x2E80, 0x2EFF),
    (0x2F00, 0x2FDF),
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x3100, 0x312F),
    (0x3130, 0x318F),
    (0x31A0, 0x31BF),
    (0x31C0, 0x31EF),
    (0x31F0, 0x31FF),
    (0x3200, 0x32FF),
    (0x3300, 0x33FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),
    (0xD7B0, 0xD7FF),
    (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x30000, 0x3134F),
)

HANGUL_CODEPOINT_RANGES = (
    (0x1100, 0x11FF),
    (0x3130, 0x318F),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7A3),
    (0xD7B0, 0xD7FF),
)


@contextlib.contextmanager
def suppress_c_stderr(enabled: bool) -> Iterator[None]:
    if not enabled:
        yield
        return

    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved_stderr, 2)
        os.close(saved_stderr)
        os.close(devnull)


def font_revision(version: str = VERSION) -> float:
    """``head.fontRevision`` for our dotted version string.

    FontForge reads only the major and minor components of ``font.version``, so
    it writes the same revision for 0.3.0, 0.3.1 and 0.3.2 and a patch release
    becomes indistinguishable from its predecessor to anything that reads
    ``head`` rather than the name records. Minor and patch become decimal places
    instead, matching the sibling families: 0.3.0 is 0.3 and 0.3.1 is 0.301.
    That stays unambiguous only while minor is below 10 and patch below 100, so
    anything larger is refused rather than shipped as a colliding revision.
    """
    parts = version.split(".")
    if len(parts) not in (2, 3):
        raise ValueError(f"Expected a major.minor[.patch] version: {version}")
    major, minor = int(parts[0]), int(parts[1])
    patch = int(parts[2]) if len(parts) == 3 else 0
    if not 0 <= minor < 10 or not 0 <= patch < 100:
        raise ValueError(
            f"Version {version} cannot be mapped to a unique head.fontRevision; "
            "pick a wider encoding before releasing it."
        )
    return round(major + minor / 10 + patch / 1000, 6)


def finalize_font_metadata(output_path: Path) -> float:
    """Finalize numeric revision and the OS/2 table version atomically."""
    from fontTools.ttLib import TTFont

    revision = font_revision()
    font = TTFont(str(output_path))
    temporary_path = output_path.with_suffix(output_path.suffix + ".rev-tmp")
    try:
        font["head"].fontRevision = revision
        os2_table = font["OS/2"]
        os2_table.version = max(os2_table.version, 4)
        os2_table.fsType = 0
        font.save(str(temporary_path))
    finally:
        font.close()

    os.replace(temporary_path, output_path)
    return revision


def gpos_xadvance_pairs(font) -> dict[tuple[int, int], int]:
    if "GPOS" not in font:
        return {}

    glyph_order = font.getGlyphOrder()
    glyph_ids = {name: index for index, name in enumerate(glyph_order)}
    pairs: dict[tuple[int, int], int] = {}
    for lookup in font["GPOS"].table.LookupList.Lookup:
        if lookup.LookupType != 2:
            continue
        for subtable in lookup.SubTable:
            if subtable.Format == 1:
                for first, pair_set in zip(
                    subtable.Coverage.glyphs, subtable.PairSet
                ):
                    for record in pair_set.PairValueRecord:
                        value = (
                            getattr(record.Value1, "XAdvance", 0)
                            if record.Value1 is not None
                            else 0
                        )
                        if not value:
                            continue
                        key = (glyph_ids[first], glyph_ids[record.SecondGlyph])
                        pairs[key] = pairs.get(key, 0) + value
            elif subtable.Format == 2:
                class2_glyphs: dict[int, list[str]] = {}
                for glyph_name, class_index in subtable.ClassDef2.classDefs.items():
                    class2_glyphs.setdefault(class_index, []).append(glyph_name)
                for first in subtable.Coverage.glyphs:
                    class1 = subtable.ClassDef1.classDefs.get(first, 0)
                    row = subtable.Class1Record[class1]
                    for class2, record in enumerate(row.Class2Record):
                        value = (
                            getattr(record.Value1, "XAdvance", 0)
                            if record.Value1 is not None
                            else 0
                        )
                        if not value:
                            continue
                        if class2 == 0:
                            seconds = [
                                name
                                for name in glyph_order
                                if subtable.ClassDef2.classDefs.get(name, 0) == 0
                            ]
                        else:
                            seconds = class2_glyphs.get(class2, [])
                        for second in seconds:
                            key = (glyph_ids[first], glyph_ids[second])
                            pairs[key] = pairs.get(key, 0) + value
    return pairs


def gpos_language_systems(font) -> list[tuple[str, str]]:
    if "GPOS" not in font:
        return [("DFLT", "dflt")]
    systems = []
    for script_record in font["GPOS"].table.ScriptList.ScriptRecord:
        script = script_record.Script
        if script.DefaultLangSys is not None:
            systems.append((script_record.ScriptTag, "dflt"))
        systems.extend(
            (script_record.ScriptTag, language.LangSysTag)
            for language in script.LangSysRecord
        )
    return systems or [("DFLT", "dflt")]


def interpolate_gpos_kerning(
    output_path: Path,
    lower_path: Path,
    upper_path: Path,
    amount: float,
    en_lower_path: Path | None = None,
    en_upper_path: Path | None = None,
    en_amount: float | None = None,
    graft_name_map: dict[str, tuple[str, str]] | None = None,
) -> tuple[int, int]:
    """Interpolate metrics/kerning, including grafted EN layout values."""
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.ttLib import TTFont

    lower = TTFont(str(lower_path))
    upper = TTFont(str(upper_path))
    output = TTFont(str(output_path))
    en_lower = TTFont(str(en_lower_path)) if en_lower_path is not None else None
    en_upper = TTFont(str(en_upper_path)) if en_upper_path is not None else None
    temporary_path = output_path.with_suffix(output_path.suffix + ".kern-tmp")
    try:
        if not (
            len(lower.getGlyphOrder())
            == len(upper.getGlyphOrder())
            == len(output.getGlyphOrder())
        ):
            raise ValueError("Cannot interpolate kerning across different glyph sets")

        lower_order = lower.getGlyphOrder()
        upper_order = upper.getGlyphOrder()
        output_order = output.getGlyphOrder()
        for glyph_id, output_name in enumerate(output_order):
            lower_advance, lower_lsb = lower["hmtx"].metrics[lower_order[glyph_id]]
            upper_advance, upper_lsb = upper["hmtx"].metrics[upper_order[glyph_id]]
            output["hmtx"].metrics[output_name] = (
                interpolate_advance_width(lower_advance, upper_advance, amount),
                round(interpolate_number(lower_lsb, upper_lsb, amount)),
            )

        lower_pairs = gpos_xadvance_pairs(lower)
        upper_pairs = gpos_xadvance_pairs(upper)
        interpolated_pairs = {
            pair: round(
                interpolate_number(
                    lower_pairs.get(pair, 0), upper_pairs.get(pair, 0), amount
                )
            )
            for pair in lower_pairs.keys() | upper_pairs.keys()
        }
        interpolated_pairs = {
            pair: value for pair, value in interpolated_pairs.items() if value
        }

        glyph_order = output.getGlyphOrder()
        grafted_pairs = 0
        if (
            en_lower is not None
            and en_upper is not None
            and en_amount is not None
            and graft_name_map
        ):
            output_gids = {name: gid for gid, name in enumerate(glyph_order)}
            en_lower_order = en_lower.getGlyphOrder()
            en_upper_order = en_upper.getGlyphOrder()
            en_lower_gids = {name: gid for gid, name in enumerate(en_lower_order)}
            en_upper_gids = {name: gid for gid, name in enumerate(en_upper_order)}
            output_to_en_gids = {
                output_gids[output_name]: (
                    en_lower_gids[en_names[0]],
                    en_upper_gids[en_names[1]],
                )
                for output_name, en_names in graft_name_map.items()
                if output_name in output_gids
                and en_names[0] in en_lower_gids
                and en_names[1] in en_upper_gids
            }
            if len(output_to_en_gids) != len(graft_name_map):
                raise ValueError("Generated font lost a grafted EN glyph mapping")
            en_lower_to_output_gid = {
                en_gids[0]: output_gid
                for output_gid, en_gids in output_to_en_gids.items()
            }
            en_upper_to_output_gid = {
                en_gids[1]: output_gid
                for output_gid, en_gids in output_to_en_gids.items()
            }

            for output_gid, (en_lower_gid, en_upper_gid) in output_to_en_gids.items():
                output_name = glyph_order[output_gid]
                en_lower_name = en_lower_order[en_lower_gid]
                en_upper_name = en_upper_order[en_upper_gid]
                lower_advance, lower_lsb = en_lower["hmtx"].metrics[en_lower_name]
                upper_advance, upper_lsb = en_upper["hmtx"].metrics[en_upper_name]
                output["hmtx"].metrics[output_name] = (
                    interpolate_advance_width(lower_advance, upper_advance, en_amount),
                    round(interpolate_number(lower_lsb, upper_lsb, en_amount)),
                )

            grafted_output_gids = set(output_to_en_gids)
            interpolated_pairs = {
                pair: value
                for pair, value in interpolated_pairs.items()
                if not (
                    pair[0] in grafted_output_gids
                    and pair[1] in grafted_output_gids
                )
            }
            en_lower_pairs = {
                (
                    en_lower_to_output_gid[left_gid],
                    en_lower_to_output_gid[right_gid],
                ): value
                for (left_gid, right_gid), value in gpos_xadvance_pairs(
                    en_lower
                ).items()
                if left_gid in en_lower_to_output_gid
                and right_gid in en_lower_to_output_gid
            }
            en_upper_pairs = {
                (
                    en_upper_to_output_gid[left_gid],
                    en_upper_to_output_gid[right_gid],
                ): value
                for (left_gid, right_gid), value in gpos_xadvance_pairs(
                    en_upper
                ).items()
                if left_gid in en_upper_to_output_gid
                and right_gid in en_upper_to_output_gid
            }
            graft_pairs = {
                pair: round(
                    interpolate_number(
                        en_lower_pairs.get(pair, 0),
                        en_upper_pairs.get(pair, 0),
                        en_amount,
                    )
                )
                for pair in en_lower_pairs.keys() | en_upper_pairs.keys()
            }
            graft_pairs = {
                pair: value for pair, value in graft_pairs.items() if value
            }
            interpolated_pairs.update(graft_pairs)
            grafted_pairs = len(graft_pairs)

        feature_lines = [
            f"languagesystem {script} {language};"
            for script, language in gpos_language_systems(output)
        ]
        feature_lines.extend(
            [
                "feature kern {",
                "  lookup InterpolatedKern {",
                "    lookupflag IgnoreMarks;",
            ]
        )
        feature_lines.extend(
            "    pos \\{left} \\{right} {value};".format(
                left=glyph_order[left_gid],
                right=glyph_order[right_gid],
                value=value,
            )
            for (left_gid, right_gid), value in sorted(interpolated_pairs.items())
        )
        feature_lines.extend(
            [
                "  } InterpolatedKern;",
                "} kern;",
            ]
        )

        if "GPOS" in output:
            del output["GPOS"]
        addOpenTypeFeaturesFromString(
            output,
            "\n".join(feature_lines),
            tables=["GPOS"],
        )
        if gpos_xadvance_pairs(output) != interpolated_pairs:
            raise ValueError("Generated kerning does not match master interpolation")
        output.save(str(temporary_path))
    finally:
        lower.close()
        upper.close()
        output.close()
        if en_lower is not None:
            en_lower.close()
        if en_upper is not None:
            en_upper.close()

    os.replace(temporary_path, output_path)
    return len(interpolated_pairs), grafted_pairs


def style_name(style: str, italic: bool) -> str:
    return f"{style} Italic" if italic else style


def postscript_style_name(style: str, italic: bool) -> str:
    return style_name(style, italic).replace(" ", "")


def output_filename(style: str, italic: bool) -> str:
    return f"{FILE_FAMILY_NAME}-{postscript_style_name(style, italic)}.otf"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build SNU Sprout from LINE Seed Sans KR masters and interpolated "
            "LINE Seed EN glyphs."
        )
    )
    parser.add_argument(
        "styles",
        nargs="*",
        help=(
            "Optional subset of styles: Thin Light Regular Medium SemiBold "
            "Bold ExtraBold Black"
        ),
    )
    italic_group = parser.add_mutually_exclusive_group()
    italic_group.add_argument(
        "--upright-only",
        action="store_true",
        help="Build only upright styles.",
    )
    italic_group.add_argument(
        "--italic-only",
        action="store_true",
        help="Build only italic styles.",
    )
    parser.add_argument("--source-zip-url", default=DEFAULT_SOURCE_ZIP_URL)
    parser.add_argument("--en-source-zip-url", default=DEFAULT_EN_SOURCE_ZIP_URL)
    parser.add_argument("--download-dir", default=DEFAULT_DOWNLOAD_DIR)
    parser.add_argument("--source-dir", default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument(
        "--italic-angle",
        type=float,
        default=DEFAULT_ITALIC_ANGLE,
        help="Synthetic slant angle for non-CJK glyphs in italic variants.",
    )
    parser.add_argument(
        "--guard-clearance",
        type=int,
        default=DEFAULT_GUARD_CLEARANCE,
        help=(
            "Ink gap kept between a slanted glyph and the following upright "
            "CJK glyph in italic variants."
        ),
    )
    parser.add_argument(
        "--guard-bucket-size",
        type=int,
        default=DEFAULT_GUARD_BUCKET_SIZE,
        help="Geometry bucket size used to group guard kerning classes.",
    )
    parser.add_argument(
        "--no-italic-guard",
        action="store_true",
        help="Skip the italic-to-upright-CJK collision guard.",
    )
    parser.add_argument(
        "--verbose-fontforge",
        action="store_true",
        help="Show FontForge warnings emitted while opening and generating.",
    )
    return parser


def selected_style_specs(style_names: list[str]) -> list[StyleSpec]:
    known = {spec.style: spec for spec in STYLE_SPECS}
    if not style_names:
        return list(STYLE_SPECS)

    unknown = sorted(set(style_names) - set(known))
    if unknown:
        raise SystemExit("Unknown styles: " + ", ".join(unknown))
    return [known[name] for name in style_names]


def download_zip(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, destination)
    return destination


def extract_source_fonts(
    zip_path: Path, source_dir: Path, wanted_filenames: Iterable[str]
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(wanted_filenames)
    with zipfile.ZipFile(zip_path) as archive:
        members = {
            Path(name).name: name
            for name in archive.namelist()
            if name.lower().endswith(".otf")
            and "__MACOSX" not in Path(name).parts
            and not Path(name).name.startswith("._")
        }
        missing = sorted(wanted - set(members))
        if missing:
            raise SystemExit(
                "Source ZIP did not contain expected OTF file(s): "
                + ", ".join(missing)
            )
        for filename in sorted(wanted):
            destination = source_dir / filename
            if destination.exists():
                continue
            destination.write_bytes(archive.read(members[filename]))
            print(f"Fetched {destination}")


def ensure_source_fonts(args: argparse.Namespace) -> dict[str, Path]:
    source_dir = Path(args.source_dir)
    masters = {
        label: source_dir / filename
        for label, filename in SOURCE_FILES.items()
    }
    missing = [path.name for path in masters.values() if not path.is_file()]
    if missing and args.no_download:
        raise SystemExit(
            "Missing source fonts: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )
    if missing:
        archive_path = Path(args.download_dir) / "LINE_Seed_Sans_KR.zip"
        download_zip(args.source_zip_url, archive_path)
        extract_source_fonts(archive_path, source_dir, SOURCE_FILES.values())

    missing = [path.name for path in masters.values() if not path.is_file()]
    if missing:
        raise SystemExit(
            "Missing source fonts after download: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )
    return masters


def ensure_en_fonts(args: argparse.Namespace) -> dict[str, Path]:
    source_dir = Path(args.source_dir)
    sources = {
        label: source_dir / filename
        for label, filename in EN_SOURCE_FILES.items()
    }
    missing = [path.name for path in sources.values() if not path.is_file()]
    if missing and args.no_download:
        raise SystemExit(
            "Missing source fonts: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )

    if missing:
        archive_path = Path(args.download_dir) / "LINE_Seed_Sans_EN.zip"
        download_zip(args.en_source_zip_url, archive_path)
        extract_source_fonts(archive_path, source_dir, EN_SOURCE_FILES.values())

    missing = [path.name for path in sources.values() if not path.is_file()]
    if missing:
        raise SystemExit(
            "Missing source fonts after download: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )
    return sources


def is_cjk_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in CJK_CODEPOINT_RANGES)


def is_hangul_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in HANGUL_CODEPOINT_RANGES)


def adjust_hangul_geometry(font) -> int:
    changed = 0
    for glyph in list(font.glyphs()):
        if not is_hangul_codepoint(glyph.unicode):
            continue
        if glyph.boundingBox() == (0.0, 0.0, 0.0, 0.0):
            continue
        original_width = glyph.width
        if glyph.references:
            glyph.unlinkRef()
        glyph.transform(
            (
                HANGUL_X_SCALE,
                0,
                0,
                HANGUL_Y_SCALE,
                HANGUL_X_SHIFT,
                HANGUL_Y_SHIFT,
            )
        )
        glyph.width = (
            0
            if original_width == 0
            else round(original_width * HANGUL_ADVANCE_SCALE)
        )
        changed += 1
    return changed


def should_slant_codepoint(codepoint: int) -> bool:
    return codepoint >= 0 and not is_cjk_codepoint(codepoint)


def italic_slope(angle: float = DEFAULT_ITALIC_ANGLE) -> float:
    return math.tan(math.radians(angle))


def interpolate_number(lower: float, upper: float, amount: float) -> float:
    return lower + amount * (upper - lower)


def interpolate_advance_width(lower: float, upper: float, amount: float) -> int:
    """Interpolate an advance, retaining the heavy master on invalid extrapolation."""
    candidate = round(interpolate_number(lower, upper, amount))
    if candidate >= 0:
        return candidate
    if amount > 1 and upper >= 0:
        return round(upper)
    raise ValueError(f"Interpolated advance width is negative: {candidate}")


def interpolated_advance_widths(
    lower_path: Path, upper_path: Path, amount: float
) -> list[int]:
    """Read authoritative source advances and interpolate them by stable GID."""
    from fontTools.ttLib import TTFont

    lower = TTFont(str(lower_path))
    upper = TTFont(str(upper_path))
    try:
        lower_order = lower.getGlyphOrder()
        upper_order = upper.getGlyphOrder()
        if len(lower_order) != len(upper_order):
            raise ValueError("Cannot interpolate metrics across different glyph sets")
        return [
            interpolate_advance_width(
                lower["hmtx"].metrics[lower_name][0],
                upper["hmtx"].metrics[upper_name][0],
                amount,
            )
            for lower_name, upper_name in zip(lower_order, upper_order)
        ]
    finally:
        lower.close()
        upper.close()


def style_interpolation_amount(spec: StyleSpec) -> float | None:
    if spec.lower_label is None and spec.upper_label is None:
        if spec.interpolation_amount is not None:
            raise ValueError(
                f"{spec.style} has an amount without interpolation masters"
            )
        return None
    if spec.lower_label is None or spec.upper_label is None:
        raise ValueError(f"Incomplete interpolation masters for {spec.style}")
    if spec.interpolation_amount is None:
        raise ValueError(f"Missing interpolation amount for {spec.style}")
    return spec.interpolation_amount


def english_interpolation_amount(spec: StyleSpec) -> float | None:
    if spec.style == "ExtraBold":
        return 0.5
    if spec.style == "Black":
        return 1.0
    return None


def open_source_font(fontforge, path: Path, quiet: bool):
    with suppress_c_stderr(quiet):
        return fontforge.open(str(path))


def flatten_cid_font(font, quiet: bool) -> bool:
    if not getattr(font, "cidfontname", None):
        return False
    with suppress_c_stderr(quiet):
        font.cidFlatten()
    return True


def agl_glyph_name(codepoint: int) -> str:
    """Return the AGL-conformant (registry-neutral) name for a codepoint."""
    if codepoint <= 0xFFFF:
        return f"uni{codepoint:04X}"
    return f"u{codepoint:04X}"


def codepoint_from_agl_name(glyph_name: str) -> int | None:
    """Recover the codepoint from a name :func:`agl_glyph_name` produced."""
    if glyph_name.startswith("uni"):
        digits = glyph_name[3:]
        if len(digits) != 4:
            return None
    elif glyph_name.startswith("u"):
        digits = glyph_name[1:]
        if not 4 <= len(digits) <= 6:
            return None
    else:
        return None

    try:
        return int(digits, 16)
    except ValueError:
        return None


def glyph_name_codepoints(glyph_name: str) -> list[int]:
    """Return every codepoint an AGL glyph name spells out.

    A ligature name joins its components with ``_`` and a variant name carries a
    ``.suffix``, so ``uni0066_uni0069`` is the fi ligature and ``uni0021.locl``
    the Korean-localized exclamation mark. Both are unencoded, and the name is
    the only record of the glyphs they are built from. Returns an empty list for
    a name that is not written this way.
    """
    parts = glyph_name.split(".", 1)[0].split("_")
    codepoints = []
    for part in parts:
        codepoint = codepoint_from_agl_name(part)
        if codepoint is None:
            return []
        codepoints.append(codepoint)
    return codepoints


def slants_in_italic(
    glyph_name: str, encoded_codepoints: Iterable[int] = ()
) -> bool | None:
    """Whether an italic build slants this glyph, or ``None`` if it has no identity.

    The glyph name decides, because the builder writes the deciding codepoints
    into it: a glyph the cmap cannot reach still follows the glyphs it is
    substituted from, so the fi ligature slants with ``f`` and ``i``. Names that
    are not AGL names fall back to the codepoints the cmap maps to the glyph.
    """
    codepoints = glyph_name_codepoints(glyph_name)
    if not codepoints:
        if not encoded_codepoints:
            return None
        codepoints = [min(encoded_codepoints)]
    return all(should_slant_codepoint(codepoint) for codepoint in codepoints)


def neutralize_cid_glyph_names(font, quiet: bool) -> int:
    """Rename flattened glyphs to AGL Unicode names.

    The upstream masters are CID-keyed with ROS ``(Adobe, Korea1, 2)`` but use
    an identity CID assignment (CID == GID) that does *not* follow the real
    Adobe-Korea1 glyph ordering. After ``cidFlatten`` FontForge names glyphs
    ``Korea1.<cid>``; macOS Core Text recognises that registered ordering and
    resolves those glyphs through the *standard* Adobe-Korea1 (UniKS) CMap
    instead of the font ``cmap``. Because the masters' identity CIDs differ from
    the standard Adobe-Korea1 CIDs for many syllables, the wrong glyph is shown
    (e.g. 겧 renders as 쨬). Renaming encoded glyphs to registry-neutral AGL
    names (``uniXXXX`` / ``uXXXXXX``) drops the Adobe ordering association, so
    every renderer honours the font ``cmap``.

    Glyphs no codepoint maps to are renamed as well, after the encoded ones so
    they can be named for their inputs: they carry the same ``Korea1.<cid>``
    names, and they are what ``liga``, ``calt``, and ``locl`` substitute in.
    """
    renamed = 0
    with suppress_c_stderr(quiet):
        for glyph in font.glyphs():
            codepoint = glyph.unicode
            if codepoint is None or codepoint < 0:
                continue
            new_name = agl_glyph_name(codepoint)
            if glyph.glyphname == new_name:
                continue
            glyph.glyphname = new_name
            renamed += 1
        renamed += neutralize_unencoded_glyph_names(font)
    return renamed


def gsub_subtable_features(font) -> dict[str, str]:
    """Map every GSUB subtable name to the feature tag that reaches it.

    Contextual lookups call nested subtables that no feature lists directly;
    those map to an empty tag.
    """
    tags = {}
    for lookup in font.gsub_lookups:
        _, _, features = font.getLookupInfo(lookup)
        tag = features[0][0] if features else ""
        for subtable in font.getLookupSubtables(lookup):
            tags[subtable] = tag
    return tags


def derived_glyph_names(font) -> dict[str, str]:
    """Name every substitution output after the glyphs it is substituted from.

    A ligature takes the AGL ligature name of its components
    (``uni0066_uni0069``) and a single or alternate substitution takes its input
    plus the feature that asks for it (``uni0021.locl``). Both spell out the
    codepoints behind an unencoded glyph, which is what :func:`slants_in_italic`
    reads back, and neither name belongs to a glyph registry.
    """
    feature_tags = gsub_subtable_features(font)
    names: dict[str, str] = {}
    for glyph in font.glyphs():
        for subtable, kind, *operands in glyph.getPosSub("*"):
            if kind == "Ligature":
                names.setdefault(glyph.glyphname, "_".join(operands))
            elif kind in ("Substitution", "AltSubs", "MultSubs"):
                suffix = feature_tags.get(subtable) or "alt"
                for output in operands:
                    names.setdefault(output, f"{glyph.glyphname}.{suffix}")
    return names


def unique_glyph_name(preferred: str, taken: set[str]) -> str:
    """Return ``preferred``, or the first free ``preferred<n>``, and claim it."""
    name = preferred
    index = 1
    while name in taken:
        index += 1
        name = f"{preferred}{index}"
    taken.add(name)
    return name


def neutralize_unencoded_glyph_names(font) -> int:
    """Rename the glyphs no codepoint reaches, keeping their inputs readable."""
    derived = derived_glyph_names(font)
    taken = {glyph.glyphname for glyph in font.glyphs()}
    renamed = 0
    for glyph in font.glyphs():
        if glyph.unicode is not None and glyph.unicode >= 0:
            continue
        if glyph.glyphname == ".notdef":
            continue
        preferred = derived.get(glyph.glyphname)
        if preferred is None:
            # Nothing substitutes this glyph in, so only the Adobe ordering
            # prefix has to go.
            preferred = UNENCODED_NAME_PREFIX + glyph.glyphname.rsplit(".", 1)[-1]
        if preferred == glyph.glyphname:
            continue
        taken.discard(glyph.glyphname)
        glyph.glyphname = unique_glyph_name(preferred, taken)
        renamed += 1
    return renamed


def neutralize_source_glyph_names(font, quiet: bool) -> dict[str, str]:
    """Neutralize a graft source while retaining each glyph's original name."""
    original_by_name = {}
    with suppress_c_stderr(quiet):
        for glyph in list(font.glyphs()):
            codepoint = glyph.unicode
            if codepoint is None or codepoint < 0:
                continue
            original_name = glyph.glyphname
            glyph.glyphname = agl_glyph_name(codepoint)
            original_by_name[glyph.glyphname] = original_name

        derived = derived_glyph_names(font)
        taken = {glyph.glyphname for glyph in font.glyphs()}
        for glyph in list(font.glyphs()):
            if glyph.unicode is not None and glyph.unicode >= 0:
                continue
            if glyph.glyphname == ".notdef":
                continue
            original_name = glyph.glyphname
            preferred = derived.get(original_name)
            if preferred is None:
                preferred = UNENCODED_NAME_PREFIX + original_name.rsplit(".", 1)[-1]
            taken.discard(original_name)
            glyph.glyphname = unique_glyph_name(preferred, taken)
            original_by_name[glyph.glyphname] = original_name
    return original_by_name


def glyph_outline_width(font, codepoint: int) -> float:
    for glyph in font.glyphs():
        if glyph.unicode == codepoint:
            xmin, _, xmax, _ = glyph.boundingBox()
            return xmax - xmin
    return 0


def glyph_identity(glyph) -> tuple[str, int | str]:
    codepoint = glyph.unicode
    if codepoint is not None and codepoint >= 0:
        return ("unicode", codepoint)
    return ("name", glyph.glyphname)


def glyph_map(font) -> dict[tuple[str, int | str], object]:
    return {glyph_identity(glyph): glyph for glyph in font.glyphs()}


def decompose_references(font) -> None:
    for glyph in font.glyphs():
        if glyph.references:
            glyph.unlinkRef()


def layer_signature(layer) -> tuple[tuple[bool, tuple[bool, ...]], ...]:
    return tuple(
        (contour.closed, tuple(point.on_curve for point in contour))
        for contour in layer
    )


def max_point_distance(left_layer, right_layer) -> float:
    distances = (
        math.hypot(left.x - right.x, left.y - right.y)
        for left_contour, right_contour in zip(left_layer, right_layer)
        for left, right in zip(left_contour, right_contour)
    )
    return max(distances, default=0.0)


def align_source_glyph_to_tt_bounds(glyph, glyph_set, original_name: str) -> None:
    """Align FontForge's imported CFF layer with authoritative OTF bounds."""
    from fontTools.pens.boundsPen import BoundsPen

    bounds_pen = BoundsPen(glyph_set)
    glyph_set[original_name].draw(bounds_pen)
    if bounds_pen.bounds is None:
        return
    imported_bounds = glyph.boundingBox()
    glyph.transform(
        (
            1,
            0,
            0,
            1,
            bounds_pen.bounds[0] - imported_bounds[0],
            bounds_pen.bounds[1] - imported_bounds[1],
        )
    )


def graft_english_glyphs(
    fontforge,
    output_font,
    lower_source_path: Path,
    upper_source_path: Path,
    amount: float,
    quiet: bool,
) -> tuple[dict[str, tuple[str, str]], int]:
    """Replace shared non-CJK glyphs with LINE Seed EN interpolation."""
    from fontTools.ttLib import TTFont

    source_fonts = [
        open_source_font(fontforge, lower_source_path, quiet),
        open_source_font(fontforge, upper_source_path, quiet),
    ]
    source_ttfonts = [TTFont(str(lower_source_path)), TTFont(str(upper_source_path))]
    try:
        for source_font in source_fonts:
            decompose_references(source_font)
        original_by_name = [
            neutralize_source_glyph_names(source_font, quiet)
            for source_font in source_fonts
        ]
        source_by_name = [
            {glyph.glyphname: glyph for glyph in source_font.glyphs()}
            for source_font in source_fonts
        ]
        source_glyph_sets = [font.getGlyphSet() for font in source_ttfonts]

        graft_name_map = {}
        with suppress_c_stderr(quiet):
            for output_glyph in output_font.glyphs():
                codepoints = glyph_name_codepoints(output_glyph.glyphname)
                if not codepoints or min(codepoints) < 0x20 or not all(
                    should_slant_codepoint(codepoint) for codepoint in codepoints
                ):
                    continue
                source_glyphs = [
                    glyphs.get(output_glyph.glyphname) for glyphs in source_by_name
                ]
                if any(glyph is None for glyph in source_glyphs):
                    continue
                original_names = tuple(
                    names[output_glyph.glyphname] for names in original_by_name
                )
                for source_glyph, glyph_set, original_name in zip(
                    source_glyphs, source_glyph_sets, original_names
                ):
                    align_source_glyph_to_tt_bounds(
                        source_glyph, glyph_set, original_name
                    )

                if amount == 0:
                    interpolated_layer = source_glyphs[0].foreground.dup()
                elif amount == 1:
                    interpolated_layer = source_glyphs[1].foreground.dup()
                else:
                    interpolated_layer = safe_interpolated_layer(
                        source_glyphs[0], source_glyphs[1], amount
                    )
                if interpolated_layer is not None:
                    output_glyph.foreground = interpolated_layer
                else:
                    output_glyph.foreground = source_glyphs[0].foreground
                    expected_bounds = interpolate_bounds(
                        source_glyphs[0].boundingBox(),
                        source_glyphs[1].boundingBox(),
                        amount,
                    )
                    target_area = interpolate_number(
                        layer_ink_area(source_glyphs[0].foreground),
                        layer_ink_area(source_glyphs[1].foreground),
                        amount,
                    )
                    fit_fallback_to_area(
                        output_glyph, expected_bounds, target_area, 1
                    )

                lower_advance = source_ttfonts[0]["hmtx"].metrics[original_names[0]][0]
                upper_advance = source_ttfonts[1]["hmtx"].metrics[original_names[1]][0]
                output_glyph.width = interpolate_advance_width(
                    lower_advance, upper_advance, amount
                )
                graft_name_map[output_glyph.glyphname] = original_names
        return graft_name_map, len(graft_name_map)
    finally:
        for source_font in source_fonts:
            source_font.close()
        for source_ttfont in source_ttfonts:
            source_ttfont.close()


def interpolate_bounds(
    lower: tuple[float, float, float, float],
    upper: tuple[float, float, float, float],
    amount: float,
) -> tuple[float, float, float, float]:
    return tuple(
        interpolate_number(lower_value, upper_value, amount)
        for lower_value, upper_value in zip(lower, upper)
    )


def bounds_error(
    actual: tuple[float, float, float, float],
    expected: tuple[float, float, float, float],
) -> float:
    return max(
        abs(actual_value - expected_value)
        for actual_value, expected_value in zip(actual, expected)
    )


def layer_ink_area(layer) -> float:
    from fontTools.pens.areaPen import AreaPen

    pen = AreaPen(None)
    layer.draw(pen)
    return abs(pen.value)


def safe_interpolated_layer(lower_glyph, upper_glyph, amount: float):
    """Return a direct outline interpolation only when it is geometrically safe."""
    lower_layer = lower_glyph.foreground
    upper_layer = upper_glyph.foreground
    if layer_signature(lower_layer) != layer_signature(upper_layer):
        return None
    if (
        max_point_distance(lower_layer, upper_layer)
        > INTERPOLATION_POINT_DISTANCE_LIMIT
    ):
        return None

    layer = lower_layer.interpolateNewLayer(upper_layer, amount)
    expected_bounds = interpolate_bounds(
        lower_glyph.boundingBox(), upper_glyph.boundingBox(), amount
    )
    if bounds_error(layer.boundingBox(), expected_bounds) > INTERPOLATION_BOUNDS_TOLERANCE:
        return None
    if 0 <= amount <= 1:
        lower_area = layer_ink_area(lower_layer)
        upper_area = layer_ink_area(upper_layer)
        interpolated_area = layer_ink_area(layer)
        if not (
            min(lower_area, upper_area) - INTERPOLATION_AREA_TOLERANCE
            <= interpolated_area
            <= max(lower_area, upper_area) + INTERPOLATION_AREA_TOLERANCE
        ):
            return None
    return layer


def fit_glyph_to_bounds(
    glyph, target: tuple[float, float, float, float]
) -> None:
    current = glyph.boundingBox()
    current_width = current[2] - current[0]
    current_height = current[3] - current[1]
    target_width = target[2] - target[0]
    target_height = target[3] - target[1]
    if current_width <= 0 or current_height <= 0:
        return
    if target_width <= 0 or target_height <= 0:
        return

    x_scale = target_width / current_width
    y_scale = target_height / current_height
    x_shift = target[0] - x_scale * current[0]
    y_shift = target[1] - y_scale * current[1]
    glyph.transform((x_scale, 0, 0, y_scale, x_shift, y_shift))


def fit_fallback_to_area(
    glyph,
    target_bounds: tuple[float, float, float, float],
    target_area: float,
    initial_stroke_width: float,
) -> float:
    """Fit an incompatible outline to interpolated bounds and ink weight."""
    source_layer = glyph.foreground.dup()
    candidates = []

    def render(stroke_width: float) -> float:
        glyph.foreground = source_layer
        if stroke_width:
            glyph.changeWeight(stroke_width, "auto", 0, 0, "squish")
        fit_glyph_to_bounds(glyph, target_bounds)
        area = layer_ink_area(glyph.foreground)
        candidates.append((abs(area - target_area), glyph.foreground.dup(), area))
        return area

    base_area = render(0)
    if abs(base_area - target_area) <= INTERPOLATION_AREA_TOLERANCE:
        return base_area
    if target_area < base_area:
        return base_area

    outer_stroke = max(abs(initial_stroke_width), 1)
    outer_area = render(outer_stroke)

    if min(base_area, outer_area) <= target_area <= max(base_area, outer_area):
        inner_stroke = 0.0
        inner_area = base_area
        for _ in range(FALLBACK_AREA_SEARCH_STEPS):
            area_delta = outer_area - inner_area
            if not area_delta:
                break
            stroke_width = round(
                inner_stroke
                + (target_area - inner_area)
                * (outer_stroke - inner_stroke)
                / area_delta
            )
            if stroke_width in (inner_stroke, outer_stroke):
                break
            area = render(stroke_width)
            if abs(area - target_area) <= INTERPOLATION_AREA_TOLERANCE:
                break
            if min(inner_area, area) <= target_area <= max(inner_area, area):
                outer_stroke, outer_area = stroke_width, area
            else:
                inner_stroke, inner_area = stroke_width, area
    elif outer_area > base_area and target_area > outer_area:
        base_layer = candidates[0][1]
        outer_layer = candidates[1][1]
        if layer_signature(base_layer) == layer_signature(outer_layer):
            layer_amount = (target_area - base_area) / (outer_area - base_area)
            for _ in range(FALLBACK_AREA_SEARCH_STEPS):
                layer = base_layer.interpolateNewLayer(outer_layer, layer_amount)
                glyph.foreground = layer
                fit_glyph_to_bounds(glyph, target_bounds)
                area = layer_ink_area(glyph.foreground)
                candidates.append(
                    (abs(area - target_area), glyph.foreground.dup(), area)
                )
                if abs(area - target_area) <= INTERPOLATION_AREA_TOLERANCE:
                    break
                area_delta = area - base_area
                if area_delta <= 0:
                    break
                layer_amount *= (target_area - base_area) / area_delta

    _, best_layer, best_area = min(candidates, key=lambda candidate: candidate[0])
    glyph.foreground = best_layer
    return best_area


def fallback_stroke_width(
    spec: StyleSpec, lower_font, upper_font, amount: float
) -> int:
    lower_width = glyph_outline_width(lower_font, INTERPOLATION_REFERENCE_CODEPOINT)
    upper_width = glyph_outline_width(upper_font, INTERPOLATION_REFERENCE_CODEPOINT)
    if spec.source_label == spec.lower_label:
        source_amount = 0.0
    elif spec.source_label == spec.upper_label:
        source_amount = 1.0
    else:
        raise ValueError(f"{spec.style} source is not an interpolation endpoint")
    delta = (amount - source_amount) * (upper_width - lower_width)
    if delta < 0:
        raise ValueError(f"{spec.style} requires unsupported outline thinning")
    return round(delta)


def apply_interpolated_weight(
    output_font,
    lower_font,
    upper_font,
    spec: StyleSpec,
    amount: float,
    advance_widths: list[int],
    quiet: bool,
) -> InterpolationStats:
    decompose_references(output_font)
    decompose_references(lower_font)
    decompose_references(upper_font)
    lower_glyphs = glyph_map(lower_font)
    upper_glyphs = glyph_map(upper_font)
    stroke_width = fallback_stroke_width(spec, lower_font, upper_font, amount)

    matched = direct = fallback = missing = 0
    with suppress_c_stderr(quiet):
        for output_glyph in output_font.glyphs():
            identity = glyph_identity(output_glyph)
            lower_glyph = lower_glyphs.get(identity)
            upper_glyph = upper_glyphs.get(identity)
            if lower_glyph is None or upper_glyph is None:
                missing += 1
                continue

            matched += 1
            expected_bounds = interpolate_bounds(
                lower_glyph.boundingBox(), upper_glyph.boundingBox(), amount
            )
            interpolated_layer = safe_interpolated_layer(
                lower_glyph, upper_glyph, amount
            )
            if interpolated_layer is not None:
                output_glyph.foreground = interpolated_layer
                direct += 1
            else:
                lower_area = layer_ink_area(lower_glyph.foreground)
                upper_area = layer_ink_area(upper_glyph.foreground)
                target_area = interpolate_number(lower_area, upper_area, amount)
                fitted_area = fit_fallback_to_area(
                    output_glyph,
                    expected_bounds,
                    target_area,
                    stroke_width,
                )
                if 0 <= amount <= 1 and not (
                    min(lower_area, upper_area) - INTERPOLATION_AREA_TOLERANCE
                    <= fitted_area
                    <= max(lower_area, upper_area) + INTERPOLATION_AREA_TOLERANCE
                ):
                    raise ValueError(
                        f"{spec.style} {identity} weight fell outside its masters"
                    )
                fallback += 1

            if (
                bounds_error(output_glyph.boundingBox(), expected_bounds)
                > INTERPOLATION_BOUNDS_TOLERANCE
            ):
                raise ValueError(
                    f"{spec.style} {identity} bounds do not match interpolation"
                )

            glyph_id = output_glyph.originalgid
            if not 0 <= glyph_id < len(advance_widths):
                raise ValueError(f"{spec.style} {identity} has no stable source GID")
            output_glyph.width = advance_widths[glyph_id]

    if missing:
        raise ValueError(f"{spec.style} is missing {missing} master glyphs")
    return InterpolationStats(matched, direct, fallback, missing)


def slant_non_cjk_glyphs(font, angle: float) -> tuple[int, int]:
    slope = italic_slope(angle)
    slanted = 0
    upright = 0
    for glyph in list(font.glyphs()):
        codepoint = glyph.unicode
        encoded = (codepoint,) if codepoint is not None and codepoint >= 0 else ()
        if not slants_in_italic(glyph.glyphname, encoded):
            upright += 1
            continue
        if glyph.references:
            glyph.unlinkRef()
        glyph.transform((1, 0, slope, 1, 0, 0))
        slanted += 1
    return slanted, upright


def os2_stylemap(spec: StyleSpec, italic: bool) -> int:
    stylemap = USE_TYPO_METRICS
    if italic:
        stylemap |= 1
    if spec.weight >= 700:
        stylemap |= 32
    if not italic and spec.weight == 400:
        stylemap |= 64
    return stylemap


def rewrite_metadata(font, spec: StyleSpec, italic: bool, italic_angle: float) -> None:
    output_style = style_name(spec.style, italic)
    full_name = f"{FAMILY_NAME} {output_style}"
    ps_name = f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"

    font.familyname = FAMILY_NAME
    font.fullname = full_name
    font.fontname = ps_name
    font.weight = "Normal" if spec.style == "Regular" else spec.style
    font.version = VERSION
    font.copyright = COPYRIGHT_TEXT
    font.italicangle = italic_angle
    font.os2_weight = spec.weight
    font.os2_width = 5
    font.os2_fstype = 0
    font.os2_vendor = "SNUS"
    font.os2_stylemap = os2_stylemap(spec, italic)
    panose = list(font.os2_panose)
    panose[2] = PANOSE_WEIGHT_NO_FIT
    font.os2_panose = tuple(panose)

    notice = (
        "SNU Sprout is a derivative of LINE Seed Sans KR and LINE Seed Sans "
        "and does not use the upstream family name as its primary font name."
    )
    font.sfnt_names = (
        (
            "English (US)",
            "Copyright",
            COPYRIGHT_TEXT,
        ),
        ("English (US)", "Family", FAMILY_NAME),
        ("English (US)", "SubFamily", output_style),
        ("English (US)", "UniqueID", f"{VERSION};SNUS;{ps_name}"),
        ("English (US)", "Fullname", full_name),
        ("English (US)", "Version", f"Version {VERSION}"),
        ("English (US)", "PostScriptName", ps_name),
        ("English (US)", "Trademark", notice),
        (
            "English (US)",
            "Manufacturer",
            "Seoul National University Sprout derivative build",
        ),
        ("English (US)", "Preferred Family", FAMILY_NAME),
        ("English (US)", "Preferred Styles", output_style),
        ("English (US)", "Compatible Full", full_name),
        ("English (US)", "License", LICENSE_DESCRIPTION),
        ("English (US)", "License URL", LICENSE_URL),
    )


def output_path_for(output_dir: Path, spec: StyleSpec, italic: bool) -> Path:
    return output_dir / output_filename(spec.style, italic)


# Coordinates use UPM 1000. Scale x and y equally to retain aspect ratio.
VERTICAL_FIT = {
    "hangul": {"scale": 1.0, "dy": 13.5},
    "latin": {"scale": 0.9863286857899631, "dy": 0.0},
}


def _vertical_is_hangul(cp):
    return any(a <= cp <= b for a, b in [(0x1100, 0x11ff), (0x3130, 0x318f),
               (0xa960, 0xa97f), (0xac00, 0xd7a3), (0xd7b0, 0xd7ff), (0xffa0, 0xffdc)])


def _vertical_hangul_glyphs(font):
    glyphs = {g for cp, g in font.getBestCmap().items() if _vertical_is_hangul(cp)}
    if 'GSUB' not in font:
        return glyphs
    while True:
        found = set()
        for lookup in font['GSUB'].table.LookupList.Lookup:
            for sub in lookup.SubTable:
                sub = getattr(sub, 'ExtSubTable', sub)
                for source, target in getattr(sub, 'mapping', {}).items():
                    if source in glyphs:
                        found.update([target] if isinstance(target, str) else target)
                for source, targets in getattr(sub, 'alternates', {}).items():
                    if source in glyphs:
                        found.update(targets)
                for first, ligatures in getattr(sub, 'ligatures', {}).items():
                    for ligature in ligatures:
                        if first in glyphs and all(g in glyphs for g in ligature.Component):
                            found.add(ligature.LigGlyph)
        found -= glyphs
        if not found:
            return glyphs
        glyphs.update(found)


def _vertical_walk(obj, seen=None):
    if seen is None:
        seen = set()
    if id(obj) in seen or isinstance(obj, (str, bytes, int, float, type(None))):
        return
    seen.add(id(obj))
    yield obj
    values = obj.values() if isinstance(obj, dict) else obj if isinstance(obj, (list, tuple)) else vars(obj).values() if hasattr(obj, '__dict__') else []
    for value in values:
        yield from _vertical_walk(value, seen)


def _vertical_scale_layout(font, hangul, fits):
    """Scale Latin layout and split mixed first-glyph classes in collision guards."""
    fit = fits['latin']
    scale, dy = fit['scale'], fit['dy']
    mixed_pairs = []
    for lookup in font['GPOS'].table.LookupList.Lookup:
        for sub in lookup.SubTable:
            sub = getattr(sub, 'ExtSubTable', sub)
            for key, value in vars(sub).items():
                if hasattr(value, 'glyphs'):
                    if set(value.glyphs) & hangul:
                        assert isinstance(sub,otTables.PairPos) and sub.Format == 2 and key == 'Coverage', ('unsupported Hangul positioning', key)
                        mixed_pairs.append((sub,copy.deepcopy(sub)))
            if hasattr(sub, 'PairSet'):
                for pairset in sub.PairSet:
                    for pair in pairset.PairValueRecord:
                        if pair.SecondGlyph in hangul and pair.Value2:
                            assert not any(vars(pair.Value2).values())
            if hasattr(sub, 'Class2Record'):
                raise AssertionError('Unexpected GPOS structure')
            if hasattr(sub, 'Class1Record'):
                classes = {sub.ClassDef2.classDefs.get(g, 0) for g in hangul}
                for row in sub.Class1Record:
                    for index in classes:
                        value = row.Class2Record[index].Value2
                        assert value is None or not any(vars(value).values())
    anchors = [(o, o.YCoordinate) for o in _vertical_walk(font['GPOS']) if isinstance(o, otTables.Anchor)]
    assert all(o.Format == 1 for o, _ in anchors)
    assert not any(isinstance(o, otTables.Device) for o in _vertical_walk(font['GPOS']))
    ScalerVisitor(scale).visit(font['GPOS'])
    for sub, original in mixed_pairs:
        groups = {}
        for glyph in original.Coverage.glyphs:
            key = (original.ClassDef1.classDefs.get(glyph,0), 'hangul' if glyph in hangul else 'latin')
            groups.setdefault(key,[]).append(glyph)
        sub.ClassDef1 = otTables.ClassDef()
        sub.ClassDef1.classDefs = {}
        sub.Class1Record = []
        for index, ((old_class,kind),glyphs) in enumerate(sorted(groups.items())):
            row = copy.deepcopy(original.Class1Record[old_class])
            for pair in row.Class2Record:
                if pair.Value1:
                    ScalerVisitor(fits[kind]['scale']).visit(pair.Value1)
                if pair.Value2:
                    ScalerVisitor(scale).visit(pair.Value2)
            sub.Class1Record.append(row)
            if index:
                sub.ClassDef1.classDefs.update(dict.fromkeys(glyphs,index))
        sub.Class1Count = len(sub.Class1Record)
    for anchor, old_y in anchors:
        anchor.YCoordinate = otRound(old_y * scale + dy)
    if 'GDEF' in font:
        caret = font['GDEF'].table.LigCaretList
        if caret:
            assert not set(caret.Coverage.glyphs) & hangul
        ScalerVisitor(scale).visit(font['GDEF'])


def _vertical_update_private(cff, fit):
    """Global hint zones describe the Latin; local glyph stems were transformed."""
    top = cff.topDictIndex[0]
    privates = [d.Private for d in top.FDArray] if hasattr(top, 'FDArray') else [top.Private]
    scale, dy = fit['scale'], fit['dy']
    for private in privates:
        for attr in ['BlueValues', 'OtherBlues', 'FamilyBlues', 'FamilyOtherBlues']:
            value = getattr(private, attr, None)
            if value:
                setattr(private, attr, [otRound(v*scale+dy) for v in value])
        for attr in ['StdHW', 'StdVW', 'StemSnapH', 'StemSnapV']:
            value = getattr(private, attr, None)
            if value is not None:
                setattr(private, attr, [otRound(v*scale) for v in value] if isinstance(value, list) else otRound(value*scale))
        if 'BlueScale' in private.rawDict:
            private.BlueScale /= scale


def _vertical_bounds(glyphs, name):
    pen = BoundsPen(glyphs)
    glyphs[name].draw(pen)
    return pen.bounds


def _transform_vertical_outlines(plan_path):
    import fontforge
    plan = json.loads(Path(plan_path).read_text())
    font = fontforge.open(plan['source'])
    if font.iscid:
        assert font.cidsubfontcnt == 1
        font.cidsubfont = 0
    order = plan['glyph_order']
    order_set = set(order)
    hangul = set(plan['hangul_glyphs'])
    seen = set()
    for glyph in font.glyphs():
        if font.iscid:
            name = '.notdef' if glyph.glyphname == '.notdef' else 'cid'+glyph.glyphname.rsplit('.',1)[1].zfill(5)
        else:
            gid = glyph.originalgid
            assert 0 <= gid < len(order), (glyph.glyphname, gid)
            name = order[gid]
        assert name in order_set and name not in seen, name
        seen.add(name)
        fit = plan['hangul'] if name in hangul else plan['latin']
        scale, dy = fit['scale'], fit['dy']
        width = glyph.width
        glyph.transform((scale, 0, 0, scale, 0, dy), ('round',))
        glyph.width = math.floor(width * scale + 0.5)
    assert seen == order_set
    font.generate(plan['outline_output'], flags=('opentype', 'round'))
    font.close()


def apply_vertical_fit(path):
    """Apply the adopted uniform script fit once, after all design/layout stages.

    Keep the main family identity and release version. The second FontForge
    export transforms CFF outlines and local hints; all other source tables
    stay in fontTools so cmap and GSUB are preserved exactly.
    """
    path = Path(path).resolve()
    with TemporaryDirectory(prefix='.vertical-fit-', dir=path.parent) as work:
        with TTFont(path, recalcTimestamp=False) as font:
            assert font['head'].unitsPerEm == 1000
            fit = VERTICAL_FIT
            hangul = _vertical_hangul_glyphs(font)
            intermediate = Path(work) / 'outlines.otf'
            plan = {'source': str(path), 'outline_output': str(intermediate),
                    'glyph_order': font.getGlyphOrder(),
                    'hangul_glyphs': sorted(hangul), **fit}
            plan_path = Path(work) / 'plan.json'
            plan_path.write_text(json.dumps(plan))
            worker = ("import runpy,sys; "
                      "runpy.run_path(sys.argv[1], run_name='vertical_worker')"
                      "['_transform_vertical_outlines'](sys.argv[2])")
            result = subprocess.run(
                ['fontforge', '-lang=py', '-c', worker,
                 str(Path(__file__).resolve()), str(plan_path)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            if result.returncode:
                raise RuntimeError(f"Outline fitting failed for {path}:\n{result.stdout}")
            _finish_vertical_fit(font, intermediate, path, hangul, fit)
            output = Path(work) / 'finished.otf'
            font.save(output)
        output.replace(path)


def _finish_vertical_fit(font, intermediate, path, hangul, fit):
    with TTFont(intermediate, recalcTimestamp=False) as outlines:
        assert set(outlines.getGlyphOrder()) == set(font.getGlyphOrder())
        assert outlines.getBestCmap() == font.getBestCmap()
        # Preserve source cmap and OpenType layout, avoiding a layout round-trip.
        original_glyphs = font.getGlyphSet()
        new_glyphs = outlines.getGlyphSet()
        for name in font.getGlyphOrder():
            transform = fit['hangul' if name in hangul else 'latin']
            s, dy = transform['scale'], transform['dy']
            assert outlines['hmtx'][name][0] == otRound(font['hmtx'][name][0]*s), name
            old, new = _vertical_bounds(original_glyphs, name), _vertical_bounds(new_glyphs, name)
            assert bool(old) == bool(new), name
            if old:
                expected = [old[0]*s, old[1]*s+dy, old[2]*s, old[3]*s+dy]
                error = max(abs(a-b) for a,b in zip(expected,new))
                assert error <= 1.01, (path.name, name, error)
                if 'vmtx' in font:
                    advance, tsb = font['vmtx'][name]
                    font['vmtx'][name] = advance, otRound(tsb+old[3]-new[3])
        old_cff = font['CFF '].cff
        old_top = old_cff.topDictIndex[0]
        new_cff = outlines['CFF '].cff
        new_top = new_cff.topDictIndex[0]
        # Only CFF and name-keyed hmtx are imported; preserve source glyph IDs.
        new_top.charset = font.getGlyphOrder()
        new_cff.fontNames = list(old_cff.fontNames)
        for attr in ('version', 'FamilyName', 'FullName', 'Weight', 'Notice',
                     'Copyright', 'CIDFontVersion'):
            if hasattr(old_top, attr):
                setattr(new_top, attr, getattr(old_top, attr))
        if hasattr(old_top, 'FDArray'):
            for old_fd, new_fd in zip(old_top.FDArray, new_top.FDArray):
                if hasattr(old_fd, 'FontName'):
                    new_fd.FontName = old_fd.FontName
        font['CFF '] = outlines['CFF ']
        font['hmtx'] = outlines['hmtx']
        _vertical_update_private(font['CFF '].cff, fit['latin'])
        _vertical_scale_layout(font, hangul, fit)
        hhea, os2 = font['hhea'], font['OS/2']
        hhea.ascent, hhea.descent, hhea.lineGap = 952, -241, 0
        os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = 952, -241, 0
        os2.fsSelection |= 128
        os2.version = max(4, os2.version)
        bbox = font['CFF '].cff.topDictIndex[0].FontBBox
        os2.usWinAscent = max(os2.usWinAscent, math.ceil(bbox[3]), outlines['head'].yMax, 952)
        os2.usWinDescent = max(os2.usWinDescent, -math.floor(bbox[1]), -outlines['head'].yMin, 241)
        for attr in ['ySubscriptXSize','ySubscriptYSize','ySubscriptXOffset','ySubscriptYOffset',
                     'ySuperscriptXSize','ySuperscriptYSize','ySuperscriptXOffset','ySuperscriptYOffset',
                     'yStrikeoutSize']:
            setattr(os2, attr, otRound(getattr(os2,attr)*fit['latin']['scale']))
        os2.yStrikeoutPosition = otRound(os2.yStrikeoutPosition*fit['latin']['scale']+fit['latin']['dy'])
        cmap = font.getBestCmap()
        os2.sCapHeight = otRound(_vertical_bounds(new_glyphs,cmap[ord('H')])[3])
        os2.sxHeight = otRound(_vertical_bounds(new_glyphs,cmap[ord('x')])[3])
        os2.recalcAvgCharWidth(font)
        post = font['post']
        post.underlineThickness = otRound(post.underlineThickness*fit['latin']['scale'])
        post.underlinePosition = otRound(post.underlinePosition*fit['latin']['scale']+fit['latin']['dy'])
        top = font['CFF '].cff.topDictIndex[0]
        top.UnderlinePosition, top.UnderlineThickness = post.underlinePosition, post.underlineThickness
        if 'BASE' in font:
            axis = font['BASE'].table.HorizAxis
            if axis:
                tags = axis.BaseTagList.BaselineTag
                roman = tags.index('romn')
                for record in axis.BaseScriptList.BaseScriptRecord:
                    values = record.BaseScript.BaseValues
                    values.DefaultIndex = roman
                    for tag, coord in zip(tags, values.BaseCoord):
                        assert coord.Format == 1
                        coord.Coordinate = 0 if tag == 'romn' else otRound(coord.Coordinate*fit['hangul']['scale']+fit['hangul']['dy'])


def build_variant(
    fontforge,
    args,
    masters: dict[str, Path],
    en_sources: dict[str, Path] | None,
    spec: StyleSpec,
    italic: bool,
) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    quiet = not args.verbose_fontforge
    font = open_source_font(fontforge, masters[spec.source_label], quiet)
    interpolation_amount = style_interpolation_amount(spec)
    interpolation_stats = InterpolationStats(0, 0, 0, 0)
    graft_name_map: dict[str, tuple[str, str]] = {}
    grafted_glyphs = 0

    try:
        flattened = flatten_cid_font(font, quiet)
        if interpolation_amount is not None:
            opened_fonts = []
            if spec.source_label == spec.lower_label:
                lower_font = font
            else:
                lower_font = open_source_font(
                    fontforge, masters[spec.lower_label], quiet
                )
                opened_fonts.append(lower_font)
            if spec.source_label == spec.upper_label:
                upper_font = font
            else:
                upper_font = open_source_font(
                    fontforge, masters[spec.upper_label], quiet
                )
                opened_fonts.append(upper_font)
            try:
                advance_widths = interpolated_advance_widths(
                    masters[spec.lower_label],
                    masters[spec.upper_label],
                    interpolation_amount,
                )
                if lower_font is not font:
                    flatten_cid_font(lower_font, quiet)
                if upper_font is not font:
                    flatten_cid_font(upper_font, quiet)
                interpolation_stats = apply_interpolated_weight(
                    font,
                    lower_font,
                    upper_font,
                    spec,
                    interpolation_amount,
                    advance_widths,
                    quiet,
                )
            finally:
                for opened_font in opened_fonts:
                    opened_font.close()
        renamed = neutralize_cid_glyph_names(font, quiet) if flattened else 0
        en_amount = english_interpolation_amount(spec)
        if en_amount is not None:
            if en_sources is None:
                raise ValueError(f"{spec.style} requires LINE Seed EN sources")
            graft_name_map, grafted_glyphs = graft_english_glyphs(
                fontforge,
                font,
                en_sources["Bold"],
                en_sources["ExtraBold"],
                en_amount,
                quiet,
            )
        hangul_adjusted = adjust_hangul_geometry(font)
        slanted, upright = (
            slant_non_cjk_glyphs(font, args.italic_angle) if italic else (0, 0)
        )
        italic_angle = -args.italic_angle if italic else 0
        rewrite_metadata(font, spec, italic, italic_angle)

        output_path = output_path_for(output_dir, spec, italic)
        with suppress_c_stderr(quiet):
            validation_state = font.validate()
        with suppress_c_stderr(quiet):
            # Round after interpolation and slanting for CFF printer compatibility.
            font.generate(str(output_path), flags=("opentype", "round"))
    finally:
        font.close()

    revision = finalize_font_metadata(output_path)
    interpolated_pairs = grafted_pairs = 0
    if interpolation_amount is not None:
        interpolated_pairs, grafted_pairs = interpolate_gpos_kerning(
            output_path,
            masters[spec.lower_label],
            masters[spec.upper_label],
            interpolation_amount,
            en_sources["Bold"] if graft_name_map else None,
            en_sources["ExtraBold"] if graft_name_map else None,
            english_interpolation_amount(spec),
            graft_name_map,
        )

    guard_summary = "none"
    if italic and not args.no_italic_guard:
        from add_italic_cjk_guard import guard_font_file

        guard_stats = guard_font_file(
            output_path,
            output_path,
            clearance=args.guard_clearance,
            bucket_size=args.guard_bucket_size,
        )
        guard_summary = (
            f"{guard_stats.guard_min}..{guard_stats.guard_max}"
            f"/{guard_stats.guarded_pairs}pairs"
        )

    apply_vertical_fit(output_path)

    print(
        f"{output_path}: interpolated={interpolation_stats.direct}, "
        f"interpolation_fallback={interpolation_stats.fallback}, "
        f"interpolation_missing={interpolation_stats.missing}, "
        f"interpolated_kern_pairs={interpolated_pairs}, "
        f"en_grafted_glyphs={grafted_glyphs}, "
        f"en_grafted_kern_pairs={grafted_pairs}, "
        f"hangul_adjusted={hangul_adjusted}, "
        f"hangul_transform=({HANGUL_X_SCALE:.6f},{HANGUL_Y_SCALE:.6f},"
        f"{HANGUL_X_SHIFT:.3f},{HANGUL_Y_SHIFT:.3f},"
        f"{HANGUL_ADVANCE_SCALE:.6f}), "
        f"italic_slanted={slanted}, italic_upright={upright}, "
        f"cid_flattened={flattened}, glyphs_renamed={renamed}, "
        f"head_revision={revision}, italic_guard={guard_summary}, "
        f"validate=0x{validation_state:x}"
    )
    return output_path


def main() -> None:
    args = build_parser().parse_args()

    try:
        import fontforge
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Run this script with FontForge: "
            "fontforge -lang=py -script build_snu_sprout.py"
        ) from exc

    masters = ensure_source_fonts(args)
    specs = selected_style_specs(args.styles)
    needs_en_sources = any(
        english_interpolation_amount(spec) is not None for spec in specs
    )
    en_sources = ensure_en_fonts(args) if needs_en_sources else None
    build_upright = not args.italic_only
    build_italic = not args.upright_only

    built_paths = []
    for spec in specs:
        if build_upright:
            built_paths.append(
                build_variant(
                    fontforge,
                    args,
                    masters,
                    en_sources,
                    spec,
                    italic=False,
                )
            )
        if build_italic:
            built_paths.append(
                build_variant(
                    fontforge,
                    args,
                    masters,
                    en_sources,
                    spec,
                    italic=True,
                )
            )

    print(f"Built {len(built_paths)} font(s).")


if __name__ == "__main__":
    main()
