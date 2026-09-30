"""Exercise the final pass with real CFF outlines and mixed-script OpenType data."""
import importlib.util
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.roundTools import otRound
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'build_snu_sprout.py'
spec = importlib.util.spec_from_file_location('vertical_fit_test_module', MODULE_PATH)
fit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit_module)


def make_font(path):
    # Deliberately non-alphabetic order: FontForge reorders some CFF exports.
    order = ['.notdef', 'uniAC00', 'H', 'x', 'A', 'uniAC00.alt', 'acutecomb']
    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap({0xAC00: 'uniAC00', 72: 'H', 120: 'x', 65: 'A',
                               0x301: 'acutecomb'})
    strings = {}
    for name in order:
        pen = T2CharStringPen(600, None)
        bottom, top = (-401, 1301) if name == "acutecomb" else (-20, 700)
        pen.moveTo((50, bottom))
        pen.lineTo((450, bottom))
        pen.lineTo((450, top))
        pen.lineTo((50, top))
        pen.closePath()
        strings[name] = pen.getCharString()
    builder.setupCFF('SNUFixture-Regular', {'FamilyName': 'SNU Fixture',
                      'FullName': 'SNU Fixture Regular', 'version': '0.123'},
                     strings, {})
    builder.setupHorizontalMetrics({name: (600, 50) for name in order})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupVerticalMetrics({name: (1000, 100) for name in order})
    builder.setupVerticalHeader(ascent=500, descent=-500)
    builder.setupNameTable({'familyName': 'SNU Fixture', 'styleName': 'Regular',
                           'psName': 'SNUFixture-Regular', 'version': 'Version 0.123'})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200,
                     usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.font['head'].fontRevision = 0.123
    addOpenTypeFeaturesFromString(builder.font, '''
        feature ccmp { sub uniAC00 by uniAC00.alt; } ccmp;
        @left = [A uniAC00];
        @right = [x H];
        feature kern { pos @left @right 100; } kern;
        markClass acutecomb <anchor 0 500> @top;
        feature mark { pos base A <anchor 200 700> mark @top; } mark;
    ''')
    builder.save(path)


@unittest.skipUnless(shutil.which('fontforge'), 'FontForge is required')
class VerticalFitTests(unittest.TestCase):
    def test_uniform_fit_preserves_identity_substitution_and_script_positioning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.otf'
            make_font(path)
            with TTFont(path) as before:
                names = before['name'].compile(before)
                revision = before['head'].fontRevision
                gsub = before['GSUB'].compile(before)
                order = before.getGlyphOrder()
            fit_module.apply_vertical_fit(path)
            with TTFont(path) as after:
                self.assertEqual(after['name'].compile(after), names)
                self.assertEqual(after['head'].fontRevision, revision)
                self.assertEqual(after['CFF '].cff.topDictIndex[0].version, '0.123')
                self.assertEqual(after.getGlyphOrder(), order)
                self.assertEqual(after['GSUB'].compile(after), gsub)
                self.assertEqual((after['hhea'].ascent, after['hhea'].descent,
                                  after['hhea'].lineGap), (952, -241, 0))
                os2 = after['OS/2']
                self.assertEqual((os2.sTypoAscender, os2.sTypoDescender,
                                  os2.sTypoLineGap), (952, -241, 0))
                self.assertTrue(os2.fsSelection & 128)
                glyphs = after.getGlyphSet()
                for name in order:
                    kind = 'hangul' if name.startswith('uniAC00') else 'latin'
                    fit = fit_module.VERTICAL_FIT[kind]
                    scale, dy = fit['scale'], fit['dy']
                    pen = BoundsPen(glyphs)
                    glyphs[name].draw(pen)
                    bottom, top = (-401, 1301) if name == "acutecomb" else (-20, 700)
                    expected = tuple(otRound(v * scale + (dy if i % 2 else 0))
                                     for i, v in enumerate((50, bottom, 450, top)))
                    self.assertEqual(pen.bounds, expected, name)
                    self.assertEqual(after['hmtx'][name][0], otRound(600 * scale))
                    self.assertEqual(after['vmtx'][name], (1000, 100 + top - expected[3]))
                bbox = after['CFF '].cff.topDictIndex[0].FontBBox
                self.assertGreaterEqual(os2.usWinAscent, math.ceil(bbox[3]))
                self.assertGreaterEqual(os2.usWinDescent, -math.floor(bbox[1]))
                pairs = after['GPOS'].table.LookupList.Lookup[0].SubTable[0]
                for name, kind in [('A', 'latin'), ('uniAC00', 'hangul')]:
                    c1 = pairs.ClassDef1.classDefs.get(name, 0)
                    c2 = pairs.ClassDef2.classDefs.get('x', 0)
                    value = pairs.Class1Record[c1].Class2Record[c2].Value1.XAdvance
                    self.assertEqual(value, otRound(100 * fit_module.VERTICAL_FIT[kind]['scale']))
                mark = after['GPOS'].table.LookupList.Lookup[1].SubTable[0]
                scale = fit_module.VERTICAL_FIT['latin']['scale']
                dy = fit_module.VERTICAL_FIT['latin']['dy']
                self.assertEqual(mark.MarkArray.MarkRecord[0].MarkAnchor.YCoordinate,
                                 otRound(500 * scale + dy))
                self.assertEqual(mark.BaseArray.BaseRecord[0].BaseAnchor[0].YCoordinate,
                                 otRound(700 * scale + dy))
