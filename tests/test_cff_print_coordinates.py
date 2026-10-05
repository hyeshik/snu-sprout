"""Integration check for the CFF coordinate pattern seen in HP print failures.

Run after the canonical build. A source-only checkout skips this check.
"""
from pathlib import Path
import unittest

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "instance_otf"


class CFFPrintCoordinateTests(unittest.TestCase):
    def built_fonts(self):
        paths = sorted(FONT_DIR.glob("SNUSprout-*.otf"))
        if not paths:
            self.skipTest("Run the canonical font build first")
        self.assertEqual(len(paths), 16)
        return paths

    def test_built_outlines_use_integer_coordinates(self):
        for path in self.built_fonts():
            with self.subTest(font=path.name), TTFont(path) as font:
                glyphs = font.getGlyphSet()
                fractional = []
                for name in font.getGlyphOrder():
                    pen = RecordingPen()
                    glyphs[name].draw(pen)
                    if any(
                        value != int(value)
                        for operation, points in pen.value
                        for point in points
                        if isinstance(point, tuple)
                        for value in point
                    ):
                        fractional.append(name)
                self.assertEqual(
                    len(fractional), 0,
                    f"{path.name}: {len(fractional)} glyphs have fractional "
                    f"CFF coordinates; first ten: {fractional[:10]}",
                )

    def test_built_fonts_use_a_conventional_space_without_control_aliases(self):
        for path in self.built_fonts():
            with self.subTest(font=path.name), TTFont(path) as font:
                cmap = font.getBestCmap() or {}
                self.assertEqual(cmap.get(0x20), "space")
                self.assertEqual(font.getGlyphID("space"), 1)
                self.assertGreater(font["hmtx"]["space"][0], 0)
                self.assertTrue(
                    all(codepoint not in cmap for codepoint in range(0x20))
                )
                self.assertEqual(cmap.get(0xA0), "uni00A0")
                self.assertNotEqual(font.getGlyphID("uni00A0"), 1)

                top_dict = font["CFF "].cff.topDictIndex[0]
                self.assertFalse(hasattr(top_dict, "ROS"))


if __name__ == "__main__":
    unittest.main()
