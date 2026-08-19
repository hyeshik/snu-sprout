#!/usr/bin/env python3
"""Add italic-Latin-to-upright-CJK optical guards to a generated OTF.

The italic variants shear non-CJK outlines without touching advance widths, so
a slanted glyph can lean past its own advance and collide with the following
upright CJK glyph (``f다`` is the clearest case: ``f`` overhangs its advance by
160 units while ``다`` only offers 78 units of left side bearing).

This module measures that geometry and appends a class-based GPOS pair
positioning lookup to every ``kern`` feature, adding a positive ``XAdvance`` to
the slanted glyph. Because the fix is kerning, it never inserts a space glyph
and never introduces a line-break opportunity.
"""
from __future__ import annotations

import argparse
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

from fontTools.otlLib.builder import (
    buildLookup,
    buildPairPosClassesSubtable,
    buildValue,
)
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from build_snu_sprout import slants_in_italic


DEFAULT_CLEARANCE = 30
DEFAULT_BUCKET_SIZE = 5


class GuardStats(NamedTuple):
    slanted_glyphs: int
    upright_glyphs: int
    slanted_classes: int
    upright_classes: int
    guarded_pairs: int
    guard_min: int
    guard_max: int
    lookup_index: int


def round_up(value: float, step: int) -> int:
    return int(math.ceil(value / step) * step)


def round_down(value: float, step: int) -> int:
    return int(math.floor(value / step) * step)


def guard_units(
    *,
    right_overhang: float,
    upright_left_side_bearing: float,
    clearance: int = DEFAULT_CLEARANCE,
    bucket_size: int = DEFAULT_BUCKET_SIZE,
) -> int:
    """Return the advance to add so the pair keeps ``clearance`` units of ink gap.

    Zero means the pair already clears, so no guard is emitted and the pair
    keeps its designed spacing.
    """
    required = right_overhang + clearance - upright_left_side_bearing
    if required <= 0:
        return 0
    return round_up(required, bucket_size)


def glyph_bounds(glyph_set, glyph_name: str) -> tuple[float, float, float, float] | None:
    pen = BoundsPen(glyph_set)
    glyph_set[glyph_name].draw(pen)
    return pen.bounds


def encoded_glyph_codepoints(font: TTFont) -> dict[str, set[int]]:
    codepoints: dict[str, set[int]] = defaultdict(set)
    for codepoint, glyph_name in font.getBestCmap().items():
        codepoints[glyph_name].add(codepoint)
    return codepoints


def collect_geometry_classes(
    font: TTFont,
    bucket_size: int,
) -> tuple[dict[int, tuple[str, ...]], dict[int, tuple[str, ...]]]:
    """Bucket slanted glyphs by right overhang and upright glyphs by left bearing.

    Both roundings are deliberately conservative: overhangs round up and left
    side bearings round down, so the guard computed for a class is never less
    than what any individual member of that class needs.

    Every glyph is bucketed, not only the encoded ones, because ``liga``,
    ``calt``, and ``locl`` substitute in glyphs the cmap cannot reach and those
    were slanted too. The builder's own rule decides the side, so the guard
    cannot drift away from what was sheared.
    """
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    codepoints_by_glyph = encoded_glyph_codepoints(font)
    slanted_classes: dict[int, list[str]] = defaultdict(list)
    upright_classes: dict[int, list[str]] = defaultdict(list)

    for glyph_name in font.getGlyphOrder():
        slanted = slants_in_italic(glyph_name, codepoints_by_glyph.get(glyph_name, set()))
        if slanted is None:
            continue

        bounds = glyph_bounds(glyph_set, glyph_name)
        if bounds is None:
            continue

        if not slanted:
            upright_classes[round_down(bounds[0], bucket_size)].append(glyph_name)
            continue

        advance_width = hmtx[glyph_name][0]
        right_overhang = bounds[2] - advance_width
        slanted_classes[round_up(right_overhang, bucket_size)].append(glyph_name)

    return (
        {key: tuple(sorted(value)) for key, value in slanted_classes.items()},
        {key: tuple(sorted(value)) for key, value in upright_classes.items()},
    )


def append_guard_lookup(
    font: TTFont,
    *,
    clearance: int = DEFAULT_CLEARANCE,
    bucket_size: int = DEFAULT_BUCKET_SIZE,
) -> GuardStats:
    if "GPOS" not in font:
        raise ValueError("The input font has no GPOS table.")
    if font["post"].italicAngle == 0:
        raise ValueError("The input font is not marked as italic.")

    slanted_classes, upright_classes = collect_geometry_classes(font, bucket_size)
    if not slanted_classes:
        raise ValueError("The input font has no slanted non-CJK glyphs.")
    if not upright_classes:
        raise ValueError("The input font has no upright CJK glyphs.")

    empty_value = buildValue({})
    pairs = {}
    guard_values = []
    for right_overhang, slanted_glyphs in slanted_classes.items():
        for left_side_bearing, upright_glyphs in upright_classes.items():
            guard = guard_units(
                right_overhang=right_overhang,
                upright_left_side_bearing=left_side_bearing,
                clearance=clearance,
                bucket_size=bucket_size,
            )
            if not guard:
                continue
            pairs[(slanted_glyphs, upright_glyphs)] = (
                buildValue({"XAdvance": guard}),
                empty_value,
            )
            guard_values.append(guard)

    if not pairs:
        raise ValueError("No slanted/upright pair needs a guard.")

    subtable = buildPairPosClassesSubtable(pairs, font.getReverseGlyphMap())
    lookup = buildLookup([subtable])
    gpos = font["GPOS"].table
    lookup_index = len(gpos.LookupList.Lookup)
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)

    kern_features = [
        record.Feature
        for record in gpos.FeatureList.FeatureRecord
        if record.FeatureTag == "kern"
    ]
    if not kern_features:
        raise ValueError("The input font has no GPOS kern feature.")
    for feature in kern_features:
        feature.LookupListIndex.append(lookup_index)
        feature.LookupCount = len(feature.LookupListIndex)

    return GuardStats(
        slanted_glyphs=sum(map(len, slanted_classes.values())),
        upright_glyphs=sum(map(len, upright_classes.values())),
        slanted_classes=len(slanted_classes),
        upright_classes=len(upright_classes),
        guarded_pairs=len(pairs),
        guard_min=min(guard_values),
        guard_max=max(guard_values),
        lookup_index=lookup_index,
    )


def guard_font_file(
    input_path: Path,
    output_path: Path,
    *,
    clearance: int = DEFAULT_CLEARANCE,
    bucket_size: int = DEFAULT_BUCKET_SIZE,
) -> GuardStats:
    """Append the guard lookup, rewriting ``output_path`` atomically."""
    font = TTFont(input_path)
    try:
        stats = append_guard_lookup(
            font,
            clearance=clearance,
            bucket_size=bucket_size,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_suffix(output_path.suffix + ".guard-tmp")
        font.save(temporary_path)
    finally:
        font.close()

    os.replace(temporary_path, output_path)
    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Add non-breaking italic-Latin-to-upright-CJK optical guards to a "
            "generated OTF."
        )
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--clearance", type=int, default=DEFAULT_CLEARANCE)
    parser.add_argument("--bucket-size", type=int, default=DEFAULT_BUCKET_SIZE)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    stats = guard_font_file(
        args.input,
        args.output,
        clearance=args.clearance,
        bucket_size=args.bucket_size,
    )
    print(
        f"{args.output}: slanted_glyphs={stats.slanted_glyphs}, "
        f"upright_glyphs={stats.upright_glyphs}, "
        f"slanted_classes={stats.slanted_classes}, "
        f"upright_classes={stats.upright_classes}, "
        f"guarded_pairs={stats.guarded_pairs}, "
        f"guard_range={stats.guard_min}..{stats.guard_max}, "
        f"lookup_index={stats.lookup_index}"
    )


if __name__ == "__main__":
    main()
