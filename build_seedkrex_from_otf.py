import argparse
import math
import re
import subprocess
import tempfile
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pathops
from extractor import extractUFO
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.unicodedata import script, script_extension
from ufo2ft import compileOTF
from ufoLib2 import Font


FAMILY_NAME = "SeedKRex"
DEFAULT_SOURCE_ZIP_URL = "https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip"
SOURCE_FILES = {
    "Thin": "LINESeedKR-Th.otf",
    "Regular": "LINESeedKR-Rg.otf",
    "Bold": "LINESeedKR-Bd.otf",
}
VARIANTS = [
    ("ExtraLight", 200, "Thin", -1),
    ("Thin", 250, "Thin", 0),
    ("Light", 300, "Thin", 1),
    ("Regular", 400, "Regular", 0),
    ("Medium", 500, "Regular", 1),
    ("Bold", 700, "Bold", 0),
    ("ExtraBold", 800, "Bold", 1),
]
NAME_IDS = {
    0: "Copyright (c) LY Corporation. SeedKRex is a derivative build.",
    1: FAMILY_NAME,
    2: None,
    3: None,
    4: None,
    6: None,
    7: "SeedKRex is a derivative of LINE Seed Sans KR and does not use the reserved name.",
    16: FAMILY_NAME,
    17: None,
}
NAME_PLATFORMS = [(3, 1, 0x0409), (1, 0, 0)]
ITALIC_ANGLE = 10.0
ITALIC_STYLE_SUFFIX = "Italic"
UPRIGHT_CJK_SCRIPTS = {"Bopo", "Hang", "Hani", "Hira", "Kana"}
FS_SELECTION_ITALIC = 1 << 0
FS_SELECTION_BOLD = 1 << 5
FS_SELECTION_REGULAR = 1 << 6
FS_SELECTION_OBLIQUE = 1 << 9
MAC_STYLE_BOLD = 1 << 0
MAC_STYLE_ITALIC = 1 << 1
UNICODE_NAME_RE = re.compile(
    r"^(?:uni(?P<uni>(?:[0-9A-Fa-f]{4})+)|u(?P<u>[0-9A-Fa-f]{4,6}))$"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the SeedKRex family from the three LINESeedKR OTF masters."
    )
    parser.add_argument(
        "styles",
        nargs="*",
        help="Optional subset of styles to build: ExtraLight Thin Light Regular Medium Bold ExtraBold",
    )
    italic_group = parser.add_mutually_exclusive_group()
    italic_group.add_argument(
        "--upright-only",
        action="store_true",
        help="Build only the upright styles",
    )
    italic_group.add_argument(
        "--italic-only",
        action="store_true",
        help="Build only the italic styles",
    )
    parser.add_argument(
        "--source-dir",
        default="original",
        help="Directory containing LINESeedKR-Th.otf, LINESeedKR-Rg.otf, LINESeedKR-Bd.otf",
    )
    parser.add_argument(
        "--source-zip-url",
        default=DEFAULT_SOURCE_ZIP_URL,
        help="ZIP URL used to populate missing source OTFs",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Do not auto-download missing source OTFs",
    )
    parser.add_argument(
        "--output-dir",
        default="instance_otf",
        help="Directory where the final SeedKRex OTFs will be written",
    )
    parser.add_argument(
        "--work-dir",
        help="Optional directory for temporary UFO extraction work; defaults to a temporary directory",
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="Keep the generated UFO working directory instead of deleting it",
    )
    parser.add_argument(
        "--no-hint",
        action="store_true",
        help="Skip psautohint after building the OTFs",
    )
    return parser


def midpoint(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    return ((first[0] + second[0]) / 2, (first[1] + second[1]) / 2)


def normalize_recording(pen: RecordingPen) -> RecordingPen:
    normalized = RecordingPen()
    contour: list[tuple[str, tuple]] = []

    def flush() -> None:
        nonlocal contour
        if not contour:
            return
        head_op, head_args = contour[0]
        if head_op == "qCurveTo" and head_args and head_args[-1] is None:
            offcurves = list(head_args[:-1])
            if offcurves:
                start = midpoint(offcurves[-1], offcurves[0])
                normalized.moveTo(start)
                normalized.qCurveTo(*offcurves, start)
                for op, args in contour[1:]:
                    getattr(normalized, op)(*args)
                contour = []
                return
        for op, args in contour:
            getattr(normalized, op)(*args)
        contour = []

    for command in pen.value:
        contour.append(command)
        if command[0] in {"closePath", "endPath"}:
            flush()
    flush()
    return normalized


def download_source_fonts(source_dir: Path, source_zip_url: str) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(SOURCE_FILES.values())

    with tempfile.TemporaryDirectory(prefix="seedkrex-source-zip-") as td:
        zip_path = Path(td) / "LINE_Seed_Sans_KR.zip"
        print(f"Downloading source ZIP: {source_zip_url}")
        urllib.request.urlretrieve(source_zip_url, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            members = {
                Path(name).name: name
                for name in archive.namelist()
                if name.lower().endswith(".otf")
                and not Path(name).name.startswith("._")
                and "__MACOSX" not in Path(name).parts
            }
            missing_in_zip = sorted(wanted - set(members))
            if missing_in_zip:
                raise FileNotFoundError(
                    "ZIP did not contain expected OTF files: "
                    + ", ".join(missing_in_zip)
                )
            for filename in sorted(wanted):
                destination = source_dir / filename
                if destination.exists():
                    continue
                destination.write_bytes(archive.read(members[filename]))
                print(f"Fetched {destination}")


def ensure_sources(
    source_dir: Path, source_zip_url: str, allow_download: bool
) -> dict[str, Path]:
    source_dir.mkdir(parents=True, exist_ok=True)
    missing = [
        filename for filename in SOURCE_FILES.values() if not (source_dir / filename).exists()
    ]
    if missing and allow_download:
        print("Missing source fonts detected:", ", ".join(missing))
        download_source_fonts(source_dir, source_zip_url)
        missing = [
            filename
            for filename in SOURCE_FILES.values()
            if not (source_dir / filename).exists()
        ]
    if missing:
        raise FileNotFoundError(
            "Missing source fonts: "
            + ", ".join(str(source_dir / filename) for filename in missing)
        )

    resolved: dict[str, Path] = {}
    for label, filename in SOURCE_FILES.items():
        path = source_dir / filename
        resolved[label] = path

    for label, path in resolved.items():
        font = TTFont(path)
        os2 = font["OS/2"]
        names = font["name"]
        print(
            f"{label}: {path.name} | weight={os2.usWeightClass} | "
            f"family={names.getDebugName(1)} | style={names.getDebugName(2)} | "
            f"glyphs={len(font.getGlyphOrder())}"
        )
        font.close()
    return resolved


def glyph_bounds_width(font_path: Path, codepoint: int) -> float:
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    glyph_name = font.getBestCmap()[codepoint]
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    x_min, _, x_max, _ = pen.bounds
    font.close()
    return x_max - x_min


def derive_offset_width(source_paths: dict[str, Path]) -> int:
    thin = glyph_bounds_width(source_paths["Thin"], 0x49)
    regular = glyph_bounds_width(source_paths["Regular"], 0x49)
    bold = glyph_bounds_width(source_paths["Bold"], 0x49)
    average_delta = ((regular - thin) + (bold - regular)) / 2
    offset = max(1, round(average_delta / 3))
    print(
        "Derived outline offset width:",
        offset,
        f"(I widths: Thin={thin:.1f}, Regular={regular:.1f}, Bold={bold:.1f})",
    )
    return offset


def extract_ufo_masters(source_paths: dict[str, Path], work_dir: Path) -> dict[str, Path]:
    master_dir = work_dir / "master_ufo"
    master_dir.mkdir(parents=True, exist_ok=True)
    extracted: dict[str, Path] = {}
    for label, source_path in source_paths.items():
        destination = master_dir / f"{source_path.stem}.ufo"
        ufo = Font()
        extractUFO(str(source_path), ufo)
        ufo.save(destination, overwrite=True)
        extracted[label] = destination
        print(f"Extracted {source_path.name} -> {destination}")
    return extracted


def final_style_name(base_style: str, italic: bool) -> str:
    if not italic:
        return base_style
    return f"{base_style} {ITALIC_STYLE_SUFFIX}"


def postscript_style_name(base_style: str, italic: bool) -> str:
    return final_style_name(base_style, italic).replace(" ", "")


def rewrite_names(font: TTFont, base_style: str, weight: int, italic: bool) -> None:
    style = final_style_name(base_style, italic)
    full_name = f"{FAMILY_NAME} {style}"
    ps_name = f"{FAMILY_NAME}-{postscript_style_name(base_style, italic)}"
    unique_id = f"1.000;DERV;{ps_name};{date.today().strftime('%Y%m%d')}"
    values = NAME_IDS | {
        2: style,
        3: unique_id,
        4: full_name,
        6: ps_name,
        17: style,
    }
    for name_id, value in values.items():
        if value is None:
            continue
        for platform_id, plat_enc_id, lang_id in NAME_PLATFORMS:
            font["name"].setName(value, name_id, platform_id, plat_enc_id, lang_id)

    font["OS/2"].usWeightClass = weight
    os2 = font["OS/2"]
    os2.fsSelection &= ~(
        FS_SELECTION_ITALIC | FS_SELECTION_BOLD | FS_SELECTION_REGULAR | FS_SELECTION_OBLIQUE
    )
    if italic:
        os2.fsSelection |= FS_SELECTION_ITALIC
    elif weight == 400:
        os2.fsSelection |= FS_SELECTION_REGULAR
    if weight >= 700:
        os2.fsSelection |= FS_SELECTION_BOLD

    font["head"].macStyle &= ~(MAC_STYLE_BOLD | MAC_STYLE_ITALIC)
    if weight >= 700:
        font["head"].macStyle |= MAC_STYLE_BOLD
    if italic:
        font["head"].macStyle |= MAC_STYLE_ITALIC

    slant_rise = 1000
    font["post"].italicAngle = -ITALIC_ANGLE if italic else 0
    font["hhea"].caretSlopeRise = slant_rise
    font["hhea"].caretSlopeRun = (
        round(math.tan(math.radians(ITALIC_ANGLE)) * slant_rise) if italic else 0
    )
    font["hhea"].caretOffset = 0

    cff = font["CFF "].cff
    cff.fontNames = [ps_name]
    top_dict = cff.topDictIndex[0]
    top_dict.FamilyName = FAMILY_NAME
    top_dict.FullName = full_name
    top_dict.Weight = base_style
    top_dict.Notice = (
        "SeedKRex is a derivative of LINE Seed Sans KR and does not use the reserved name."
    )


def glyph_name_codepoints(glyph_name: str) -> tuple[int, ...]:
    stem = glyph_name.split(".", 1)[0]
    match = UNICODE_NAME_RE.match(stem)
    if not match:
        return ()
    if match.group("uni"):
        text = match.group("uni")
        return tuple(int(text[index : index + 4], 16) for index in range(0, len(text), 4))
    return (int(match.group("u"), 16),)


def is_upright_cjk_codepoint(codepoint: int) -> bool:
    character = chr(codepoint)
    if script(character) in UPRIGHT_CJK_SCRIPTS:
        return True
    extensions = script_extension(character)
    return bool(extensions) and extensions <= UPRIGHT_CJK_SCRIPTS


def glyph_should_keep_upright(
    font: Font, glyph_name: str, memo: dict[str, bool], active: set[str]
) -> bool:
    if glyph_name in memo:
        return memo[glyph_name]
    if glyph_name in active:
        return False

    active.add(glyph_name)
    glyph = font[glyph_name]
    codepoints = tuple(glyph.unicodes) or glyph_name_codepoints(glyph_name)
    if codepoints:
        keep_upright = all(is_upright_cjk_codepoint(codepoint) for codepoint in codepoints)
    elif glyph.components and not glyph.contours:
        keep_upright = all(
            glyph_should_keep_upright(font, component.baseGlyph, memo, active)
            for component in glyph.components
        )
    else:
        keep_upright = False
    active.remove(glyph_name)
    memo[glyph_name] = keep_upright
    return keep_upright


def slant_glyph(font: Font, glyph_name: str, slope: float) -> None:
    glyph = font[glyph_name]
    if glyph.contours or glyph.components:
        recording = DecomposingRecordingPen(font)
        glyph.draw(recording)
        transformed = RecordingPen()
        transform = (1, 0, slope, 1, 0, 0)
        recording.replay(TransformPen(transformed, transform))
        glyph.clearContours()
        glyph.clearComponents()
        normalize_recording(transformed).replay(glyph.getPen())

    for anchor in glyph.anchors:
        anchor.x += slope * anchor.y


def italicize_font(font: Font) -> tuple[int, int]:
    memo: dict[str, bool] = {}
    active: set[str] = set()
    slope = math.tan(math.radians(ITALIC_ANGLE))
    slanted = 0
    upright = 0

    for glyph_name in font.keys():
        if glyph_should_keep_upright(font, glyph_name, memo, active):
            upright += 1
            continue
        slant_glyph(font, glyph_name, slope)
        slanted += 1

    return slanted, upright


def build_targets(
    selected_styles: set[str], build_upright: bool, build_italic: bool
) -> list[tuple[str, int, str, int, bool]]:
    variants = [item for item in VARIANTS if not selected_styles or item[0] in selected_styles]
    targets: list[tuple[str, int, str, int, bool]] = []
    for base_style, weight, source_label, offset_steps in variants:
        if build_upright:
            targets.append((base_style, weight, source_label, offset_steps, False))
        if build_italic:
            targets.append((base_style, weight, source_label, offset_steps, True))
    return targets


def offset_glyphs(font: Font, offset_width: int) -> tuple[int, int]:
    changed = 0
    skipped = 0
    operation = pathops.PathOp.UNION if offset_width > 0 else pathops.PathOp.DIFFERENCE
    magnitude = abs(offset_width)

    for glyph in font:
        if not glyph.contours:
            continue

        original = pathops.Path()
        glyph.draw(original.getPen())

        stroke = pathops.Path()
        stroke.addPath(original)
        stroke.stroke(
            magnitude,
            pathops.LineCap.BUTT_CAP,
            pathops.LineJoin.ROUND_JOIN,
            4,
        )
        stroke.convertConicsToQuads(0.01)

        try:
            adjusted = pathops.op(original, stroke, operation)
            adjusted = pathops.simplify(adjusted)
        except Exception:
            skipped += 1
            continue

        if not list(adjusted.verbs):
            skipped += 1
            continue

        glyph.clearContours()
        glyph.clearComponents()
        recording = RecordingPen()
        adjusted.draw(recording)
        normalize_recording(recording).replay(
            Qu2CuPen(glyph.getPen(), max_err=1.0, all_cubic=True)
        )
        changed += 1

    return changed, skipped


def build_variant(
    base_style: str,
    weight: int,
    source_ufo: Path,
    offset_steps: int,
    step_width: int,
    output_dir: Path,
    italic: bool,
) -> Path:
    font = Font.open(source_ufo)
    applied_width = offset_steps * step_width
    style = final_style_name(base_style, italic)
    if applied_width:
        changed, skipped = offset_glyphs(font, applied_width)
        print(
            f"{style}: applied synthetic offset {applied_width} to {changed} glyphs, skipped {skipped}"
        )
    else:
        print(f"{style}: using source master without outline offset")

    if italic:
        slanted, upright = italicize_font(font)
        print(
            f"{style}: slanted {slanted} glyphs and kept {upright} glyphs upright for CJK coverage"
        )

    otf = compileOTF(font)
    rewrite_names(otf, base_style, weight, italic)
    output_path = output_dir / f"{FAMILY_NAME}-{postscript_style_name(base_style, italic)}.otf"
    otf.save(output_path)
    print(f"Saved {output_path}")
    return output_path


def hint_outputs(paths: list[Path]) -> None:
    for path in paths:
        subprocess.run(
            ["psautohint", "--no-zones-stems", str(path)],
            check=True,
        )
        print(f"Hinted {path}")


def main() -> None:
    args = build_parser().parse_args()
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = set(args.styles)
    build_upright = not args.italic_only
    build_italic = not args.upright_only
    targets = build_targets(selected, build_upright, build_italic)
    if not targets:
        raise SystemExit("No matching styles requested.")

    source_paths = ensure_sources(
        source_dir, args.source_zip_url, allow_download=not args.no_download
    )
    step_width = derive_offset_width(source_paths)

    temporary_root: tempfile.TemporaryDirectory[str] | None = None
    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        temporary_root = tempfile.TemporaryDirectory(prefix="seedkrex-build-")
        work_dir = Path(temporary_root.name)
    print(f"Working directory: {work_dir}")

    try:
        ufo_paths = extract_ufo_masters(source_paths, work_dir)
        built_paths: list[Path] = []
        for base_style, weight, source_label, offset_steps, italic in targets:
            built_paths.append(
                build_variant(
                    base_style,
                    weight,
                    ufo_paths[source_label],
                    offset_steps,
                    step_width,
                    output_dir,
                    italic,
                )
            )
        if not args.no_hint:
            hint_outputs(built_paths)
    finally:
        if temporary_root is not None and not args.keep_work:
            temporary_root.cleanup()


if __name__ == "__main__":
    main()
