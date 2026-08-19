#!/usr/bin/env fontforge -lang=py -script
from __future__ import annotations

import argparse
import contextlib
import math
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Iterator, NamedTuple


FAMILY_NAME = "SNU Sprout"
POSTSCRIPT_FAMILY_NAME = "SNUSprout"
FILE_FAMILY_NAME = POSTSCRIPT_FAMILY_NAME
VERSION = "0.5.0"
DEFAULT_SOURCE_ZIP_URL = "https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip"
DEFAULT_DOWNLOAD_DIR = "vendor/downloads"
DEFAULT_SOURCE_DIR = "original"
DEFAULT_OUTPUT_DIR = "instance_otf"
DEFAULT_ITALIC_ANGLE = 10.0
DEFAULT_GUARD_CLEARANCE = 30
DEFAULT_GUARD_BUCKET_SIZE = 5
SYNTHETIC_WEIGHT_REFERENCE_CODEPOINT = 0x49
UNENCODED_NAME_PREFIX = "sprout"

SOURCE_FILES = {
    "Thin": "LINESeedKR-Th.otf",
    "Regular": "LINESeedKR-Rg.otf",
    "Bold": "LINESeedKR-Bd.otf",
}
MASTER_LABELS = ("Thin", "Regular", "Bold")


class StyleSpec(NamedTuple):
    style: str
    weight: int
    source_label: str
    synthetic_weight_steps: int = 0


STYLE_SPECS = (
    StyleSpec("Thin", 250, "Thin"),
    StyleSpec("Light", 300, "Thin", 1),
    StyleSpec("Regular", 400, "Regular"),
    StyleSpec("Medium", 500, "Regular", 1),
    StyleSpec("Bold", 700, "Bold"),
    StyleSpec("ExtraBold", 800, "Bold", 1),
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


def stamp_font_revision(output_path: Path) -> float:
    """Rewrite ``head.fontRevision`` on a generated OTF, atomically."""
    from fontTools.ttLib import TTFont

    revision = font_revision()
    font = TTFont(str(output_path))
    temporary_path = output_path.with_suffix(output_path.suffix + ".rev-tmp")
    try:
        font["head"].fontRevision = revision
        font.save(str(temporary_path))
    finally:
        font.close()

    os.replace(temporary_path, output_path)
    return revision


def style_name(style: str, italic: bool) -> str:
    return f"{style} Italic" if italic else style


def postscript_style_name(style: str, italic: bool) -> str:
    return style_name(style, italic).replace(" ", "")


def output_filename(style: str, italic: bool) -> str:
    return f"{FILE_FAMILY_NAME}-{postscript_style_name(style, italic)}.otf"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build SNU Sprout from LINE Seed Sans KR OTF masters."
    )
    parser.add_argument(
        "styles",
        nargs="*",
        help="Optional subset of styles: Thin Light Regular Medium Bold ExtraBold",
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


def extract_source_fonts(zip_path: Path, source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(SOURCE_FILES.values())
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
        extract_source_fonts(archive_path, source_dir)

    missing = [path.name for path in masters.values() if not path.is_file()]
    if missing:
        raise SystemExit(
            "Missing source fonts after download: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )
    return masters


def is_cjk_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in CJK_CODEPOINT_RANGES)


def should_slant_codepoint(codepoint: int) -> bool:
    return codepoint >= 0 and not is_cjk_codepoint(codepoint)


def italic_slope(angle: float = DEFAULT_ITALIC_ANGLE) -> float:
    return math.tan(math.radians(angle))


def derive_synthetic_weight_width(master_widths: list[float]) -> int:
    if len(master_widths) < 2:
        return 0
    deltas = [
        master_widths[index + 1] - master_widths[index]
        for index in range(len(master_widths) - 1)
    ]
    positive_deltas = [delta for delta in deltas if delta > 0]
    if not positive_deltas:
        return 0
    average_delta = sum(positive_deltas) / len(positive_deltas)
    return max(1, round(average_delta / 3))


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


def glyph_outline_width(font, codepoint: int) -> float:
    for glyph in font.glyphs():
        if glyph.unicode == codepoint:
            xmin, _, xmax, _ = glyph.boundingBox()
            return xmax - xmin
    return 0


def derive_synthetic_weight_width_from_sources(
    fontforge, masters: dict[str, Path], quiet: bool
) -> int:
    widths = []
    for label in MASTER_LABELS:
        font = open_source_font(fontforge, masters[label], quiet)
        try:
            flatten_cid_font(font, quiet)
            widths.append(glyph_outline_width(font, SYNTHETIC_WEIGHT_REFERENCE_CODEPOINT))
        finally:
            font.close()
    return derive_synthetic_weight_width(widths)


def apply_synthetic_weight(font, offset_width: int, quiet: bool) -> int:
    if not offset_width:
        return 0

    changed = 0
    with suppress_c_stderr(quiet):
        for glyph in list(font.glyphs()):
            if glyph.references:
                glyph.unlinkRef()
            glyph.changeWeight(offset_width, "auto", 0, 0, "auto")
            changed += 1
    return changed


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


def rewrite_metadata(font, spec: StyleSpec, italic: bool, italic_angle: float) -> None:
    output_style = style_name(spec.style, italic)
    full_name = f"{FAMILY_NAME} {output_style}"
    ps_name = f"{POSTSCRIPT_FAMILY_NAME}-{postscript_style_name(spec.style, italic)}"

    font.familyname = FAMILY_NAME
    font.fullname = full_name
    font.fontname = ps_name
    font.weight = "Normal" if spec.style == "Regular" else spec.style
    font.version = VERSION
    font.copyright = (
        "Copyright (c) LY Corporation. SNU Sprout is a derivative build."
    )
    font.italicangle = italic_angle
    font.os2_weight = spec.weight
    font.os2_width = 5
    font.os2_vendor = "SNUS"
    font.os2_stylemap = (1 if italic else 0) | (32 if spec.weight >= 700 else 0)
    if not italic and spec.weight == 400:
        font.os2_stylemap = 64

    notice = (
        "SNU Sprout is a derivative of LINE Seed Sans KR and does not use "
        "the reserved upstream family name."
    )
    font.sfnt_names = (
        (
            "English (US)",
            "Copyright",
            "Copyright (c) LY Corporation. SNU Sprout is a derivative build.",
        ),
        ("English (US)", "Family", FAMILY_NAME),
        ("English (US)", "SubFamily", output_style),
        ("English (US)", "UniqueID", f"{VERSION};SNUS;{ps_name}"),
        ("English (US)", "Fullname", full_name),
        ("English (US)", "Version", f"Version {VERSION}"),
        ("English (US)", "PostScriptName", ps_name),
        ("English (US)", "Trademark", notice),
        ("English (US)", "Manufacturer", "Seoul National University Sprout derivative build"),
        ("English (US)", "Preferred Family", FAMILY_NAME),
        ("English (US)", "Preferred Styles", output_style),
        ("English (US)", "Compatible Full", full_name),
    )


def output_path_for(output_dir: Path, spec: StyleSpec, italic: bool) -> Path:
    return output_dir / output_filename(spec.style, italic)


def build_variant(fontforge, args, masters: dict[str, Path], spec: StyleSpec, italic: bool) -> Path:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    quiet = not args.verbose_fontforge
    font = open_source_font(fontforge, masters[spec.source_label], quiet)

    try:
        flattened = flatten_cid_font(font, quiet)
        renamed = neutralize_cid_glyph_names(font, quiet) if flattened else 0
        synthetic_offset_width = spec.synthetic_weight_steps * args.synthetic_weight_width
        synthetic_changed = apply_synthetic_weight(font, synthetic_offset_width, quiet)
        slanted, upright = slant_non_cjk_glyphs(font, args.italic_angle) if italic else (0, 0)
        italic_angle = -args.italic_angle if italic else 0
        rewrite_metadata(font, spec, italic, italic_angle)

        output_path = output_path_for(output_dir, spec, italic)
        with suppress_c_stderr(quiet):
            validation_state = font.validate()
        with suppress_c_stderr(quiet):
            font.generate(str(output_path))
    finally:
        font.close()

    revision = stamp_font_revision(output_path)

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

    print(
        f"{output_path}: synthetic_weighted={synthetic_changed}, "
        f"synthetic_offset_width={synthetic_offset_width}, "
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
    build_upright = not args.italic_only
    build_italic = not args.upright_only
    args.synthetic_weight_width = derive_synthetic_weight_width_from_sources(
        fontforge,
        masters,
        not args.verbose_fontforge,
    )
    print(f"Derived synthetic weight offset width: {args.synthetic_weight_width}")

    built_paths = []
    for spec in specs:
        if build_upright:
            built_paths.append(build_variant(fontforge, args, masters, spec, italic=False))
        if build_italic:
            built_paths.append(build_variant(fontforge, args, masters, spec, italic=True))

    print(f"Built {len(built_paths)} font(s).")


if __name__ == "__main__":
    main()
