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
    def test_built_outlines_use_integer_coordinates(self):
        paths = sorted(FONT_DIR.glob("SNUSprout-*.otf"))
        if not paths:
            self.skipTest("Run the canonical font build first")
        for path in paths:
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


if __name__ == "__main__":
    unittest.main()
