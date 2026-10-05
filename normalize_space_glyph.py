"""Give U+0020 its conventional name and remove inherited control aliases."""
from __future__ import annotations

import os
from pathlib import Path

from fontTools.merge.cmap import renameCFFCharStrings
from fontTools.ttLib import TTFont


SPACE_CODEPOINT = 0x20
CONTROL_CODEPOINTS = range(0x20)


def renamed_space_glyph_order(
    glyph_order: list[str], cmap: dict[int, str]
) -> tuple[list[str], str, int]:
    old_name = cmap.get(SPACE_CODEPOINT)
    if old_name is None:
        raise ValueError("The font does not map U+0020 SPACE")
    if old_name == "space":
        return list(glyph_order), old_name, glyph_order.index(old_name)
    if "space" in glyph_order:
        raise ValueError("The font already has another glyph named 'space'")

    space_gid = glyph_order.index(old_name)
    new_order = list(glyph_order)
    new_order[space_gid] = "space"
    return new_order, old_name, space_gid


def normalize_space_glyph(path: Path) -> tuple[str, int, int]:
    """Name U+0020 ``space`` and remove controls aliased to its GID.

    LINE Seed KR maps U+0000 through U+0020 to one blank glyph. Sprout keeps
    that glyph at the same GID and width, but exposes only its real text
    character, U+0020. Other independently encoded control glyphs are retained.
    """
    path = Path(path)
    with TTFont(path, recalcTimestamp=False) as probe:
        glyph_order = probe.getGlyphOrder()
        new_order, old_name, space_gid = renamed_space_glyph_order(
            glyph_order, probe.getBestCmap() or {}
        )

    font = TTFont(path, recalcTimestamp=False)
    temporary_path = path.with_suffix(path.suffix + ".space-tmp")
    try:
        font.setGlyphOrder(new_order)
        if "CFF " not in font:
            raise ValueError("The font has no CFF table")
        cff_table = font["CFF "]
        top_dict = cff_table.cff.topDictIndex[0]
        if hasattr(top_dict, "ROS"):
            raise ValueError("Expected a name-keyed CFF font")
        if old_name != "space":
            renameCFFCharStrings(None, new_order, cff_table)

        removed = set()
        for subtable in font["cmap"].tables:
            if not subtable.isUnicode():
                continue
            for codepoint in CONTROL_CODEPOINTS:
                glyph_name = subtable.cmap.get(codepoint)
                if (
                    glyph_name is not None
                    and font.getGlyphID(glyph_name) == space_gid
                ):
                    del subtable.cmap[codepoint]
                    removed.add(codepoint)

        font.save(temporary_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        font.close()

    try:
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return old_name, space_gid, len(removed)
