import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "build_snu_sprout.py"


class FakeGlyph:
    """The slice of FontForge's glyph API the naming pass uses."""

    def __init__(self, glyphname, pos_sub):
        self.glyphname = glyphname
        self.unicode = -1 if glyphname.startswith("Korea1.") else 0x41
        self._pos_sub = pos_sub

    def getPosSub(self, subtable):
        assert subtable == "*"
        return self._pos_sub


class FakeFont:
    def __init__(self, lookups, glyphs):
        self._lookups = lookups
        self._glyphs = [FakeGlyph(name, pos_sub) for name, pos_sub in glyphs.items()]

    @property
    def gsub_lookups(self):
        return tuple(self._lookups)

    def getLookupInfo(self, lookup):
        features, _ = self._lookups[lookup]
        return "gsub_single", (), tuple((tag, ()) for tag in features)

    def getLookupSubtables(self, lookup):
        return self._lookups[lookup][1]

    def glyphs(self):
        return tuple(self._glyphs)

    def glyph_names(self):
        return [glyph.glyphname for glyph in self._glyphs]


def load_builder():
    spec = importlib.util.spec_from_file_location("build_snu_sprout", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildSnuSproutTests(unittest.TestCase):
    def test_family_names_and_source_defaults_match_project_contract(self):
        builder = load_builder()

        self.assertEqual(builder.FAMILY_NAME, "SNU Sprout")
        self.assertEqual(builder.POSTSCRIPT_FAMILY_NAME, "SNUSprout")
        self.assertEqual(builder.FILE_FAMILY_NAME, "SNUSprout")
        self.assertEqual(
            builder.DEFAULT_SOURCE_ZIP_URL,
            "https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip",
        )
        self.assertEqual(builder.DEFAULT_OUTPUT_DIR, "instance_otf")

    def test_style_matrix_keeps_current_sprout_weight_model(self):
        builder = load_builder()
        specs = {spec.style: spec for spec in builder.STYLE_SPECS}

        self.assertEqual(
            list(specs),
            ["Thin", "Light", "Regular", "Medium", "Bold", "ExtraBold"],
        )
        self.assertEqual(specs["Thin"].source_label, "Thin")
        self.assertEqual(specs["Thin"].synthetic_weight_steps, 0)
        self.assertEqual(specs["Light"].source_label, "Thin")
        self.assertEqual(specs["Light"].synthetic_weight_steps, 1)
        self.assertEqual(specs["Regular"].source_label, "Regular")
        self.assertEqual(specs["Regular"].synthetic_weight_steps, 0)
        self.assertEqual(specs["Medium"].source_label, "Regular")
        self.assertEqual(specs["Medium"].synthetic_weight_steps, 1)
        self.assertEqual(specs["Bold"].source_label, "Bold")
        self.assertEqual(specs["Bold"].synthetic_weight_steps, 0)
        self.assertEqual(specs["ExtraBold"].source_label, "Bold")
        self.assertEqual(specs["ExtraBold"].synthetic_weight_steps, 1)

    def test_fontforge_weight_synthesis_never_uses_negative_steps(self):
        builder = load_builder()

        self.assertTrue(
            all(spec.synthetic_weight_steps >= 0 for spec in builder.STYLE_SPECS)
        )

    def test_output_naming_uses_spaced_family_and_safe_file_prefix(self):
        builder = load_builder()

        self.assertEqual(builder.style_name("Regular", False), "Regular")
        self.assertEqual(builder.style_name("Regular", True), "Regular Italic")
        self.assertEqual(builder.postscript_style_name("Thin", True), "ThinItalic")
        self.assertEqual(
            builder.output_filename("Thin", True),
            "SNUSprout-ThinItalic.otf",
        )

    def test_parser_maps_source_zip_url_and_build_modes(self):
        builder = load_builder()

        args = builder.build_parser().parse_args([])
        self.assertEqual(args.source_zip_url, builder.DEFAULT_SOURCE_ZIP_URL)
        self.assertFalse(args.upright_only)
        self.assertFalse(args.italic_only)

        args = builder.build_parser().parse_args(
            ["--source-zip-url", "https://example.test/LINE_Seed_Sans_KR.zip"]
        )
        self.assertEqual(
            args.source_zip_url,
            "https://example.test/LINE_Seed_Sans_KR.zip",
        )

    def test_head_revision_distinguishes_patch_releases(self):
        builder = load_builder()

        # FontForge reads only major.minor from font.version, so it writes the
        # same head.fontRevision for 0.3.0 and 0.3.1. The builder stamps the
        # revision itself so a patch release is not mistaken for its
        # predecessor by anything reading head instead of the name records.
        self.assertEqual(builder.font_revision("0.3.0"), 0.3)
        self.assertEqual(builder.font_revision("0.3.1"), 0.301)
        self.assertEqual(builder.font_revision("0.4.0"), 0.4)
        self.assertEqual(builder.font_revision("1.0"), 1.0)
        self.assertNotEqual(
            builder.font_revision("0.3.0"), builder.font_revision("0.3.1")
        )
        self.assertEqual(builder.font_revision(), builder.font_revision(builder.VERSION))
        for ambiguous in ("0.10.0", "0.3.100", "0"):
            with self.assertRaises(ValueError):
                builder.font_revision(ambiguous)

    def test_parser_exposes_italic_guard_controls(self):
        builder = load_builder()

        args = builder.build_parser().parse_args([])
        self.assertEqual(args.guard_clearance, builder.DEFAULT_GUARD_CLEARANCE)
        self.assertEqual(args.guard_bucket_size, builder.DEFAULT_GUARD_BUCKET_SIZE)
        self.assertFalse(args.no_italic_guard)

        args = builder.build_parser().parse_args(
            ["--guard-clearance", "40", "--no-italic-guard"]
        )
        self.assertEqual(args.guard_clearance, 40)
        self.assertTrue(args.no_italic_guard)

    def test_cid_glyphs_get_registry_neutral_agl_names(self):
        builder = load_builder()

        # BMP codepoints use uniXXXX; supplementary use uXXXXXX. None of these
        # carry the "Korea1." Adobe ordering prefix that makes macOS Core Text
        # resolve glyphs through the standard Adobe-Korea1 CMap instead of the
        # font cmap (which displayed wrong syllables, e.g. 겧 as 쨬).
        self.assertEqual(builder.agl_glyph_name(0xAC00), "uniAC00")
        self.assertEqual(builder.agl_glyph_name(0xACA7), "uniACA7")
        self.assertEqual(builder.agl_glyph_name(ord("A")), "uni0041")
        self.assertEqual(builder.agl_glyph_name(0x20000), "u20000")
        self.assertFalse(builder.agl_glyph_name(0xACA7).startswith("Korea1"))

    def test_agl_names_recover_the_codepoints_that_decided_the_slant(self):
        builder = load_builder()

        self.assertEqual(builder.codepoint_from_agl_name("uni0066"), 0x66)
        self.assertEqual(builder.codepoint_from_agl_name("uniB2E4"), 0xB2E4)
        self.assertEqual(builder.codepoint_from_agl_name("u20000"), 0x20000)
        self.assertIsNone(builder.codepoint_from_agl_name("Korea1.1234"))
        self.assertIsNone(builder.codepoint_from_agl_name(".notdef"))
        self.assertIsNone(builder.codepoint_from_agl_name("uniZZZZ"))

        # A ligature spells out every component, a variant drops its suffix.
        self.assertEqual(builder.glyph_name_codepoints("uni0066_uni0069"), [0x66, 0x69])
        self.assertEqual(
            builder.glyph_name_codepoints("uni0066_uni0066_uni006C"),
            [0x66, 0x66, 0x6C],
        )
        self.assertEqual(builder.glyph_name_codepoints("uni0021.locl"), [0x21])
        self.assertEqual(builder.glyph_name_codepoints("sprout12270"), [])

    def test_substituted_glyphs_are_named_for_the_glyphs_they_come_from(self):
        builder = load_builder()
        font = FakeFont(
            lookups={
                "liga lookup": (("liga",), ("liga subtable",)),
                "locl lookup": (("locl",), ("locl subtable",)),
                "nested lookup": ((), ("nested subtable",)),
            },
            glyphs={
                "uni0066": (),
                "uni0069": (),
                "uni0021": (("locl subtable", "Substitution", "Korea1.12282"),),
                "uni006A": (("nested subtable", "Substitution", "Korea1.12258"),),
                "Korea1.12263": (("liga subtable", "Ligature", "uni0066", "uni0069"),),
                "Korea1.12282": (),
                "Korea1.12258": (),
                "Korea1.12270": (),
            },
        )

        self.assertEqual(
            builder.derived_glyph_names(font),
            {
                "Korea1.12282": "uni0021.locl",
                # A contextual lookup no feature lists still names its output.
                "Korea1.12258": "uni006A.alt",
                "Korea1.12263": "uni0066_uni0069",
            },
        )

        renamed = builder.neutralize_unencoded_glyph_names(font)

        self.assertEqual(renamed, 4)
        self.assertEqual(
            font.glyph_names()[-4:],
            [
                "uni0066_uni0069",
                "uni0021.locl",
                "uni006A.alt",
                # Nothing substitutes this one in, so it only loses the Adobe
                # ordering prefix that makes macOS resolve it through the
                # standard Adobe-Korea1 CMap.
                "sprout12270",
            ],
        )

    def test_glyph_names_stay_unique_when_two_variants_share_a_source(self):
        builder = load_builder()

        taken = {"uni006A.alt"}
        self.assertEqual(builder.unique_glyph_name("uni006A.alt", taken), "uni006A.alt2")
        self.assertEqual(builder.unique_glyph_name("uni006A.alt", taken), "uni006A.alt3")

    def test_substituted_glyphs_follow_the_glyphs_they_are_built_from(self):
        builder = load_builder()

        # fi, ffl and the Korean-localized exclamation mark are unencoded, so
        # the slant decision has to come from the glyphs they replace.
        self.assertTrue(builder.slants_in_italic("uni0066_uni0069"))
        self.assertTrue(builder.slants_in_italic("uni0066_uni0066_uni006C"))
        self.assertTrue(builder.slants_in_italic("uni0021.locl"))
        self.assertFalse(builder.slants_in_italic("uniAC00"))
        self.assertFalse(builder.slants_in_italic("uni0066_uniAC00"))
        # No readable identity: neither side of the guard may claim it.
        self.assertIsNone(builder.slants_in_italic("sprout12270"))
        self.assertIsNone(builder.slants_in_italic(".notdef"))
        # An unreadable name falls back to what the cmap maps to the glyph.
        self.assertTrue(builder.slants_in_italic("f.alt", {0x66}))
        self.assertFalse(builder.slants_in_italic("uni.alt", {0xAC00}))

    def test_italic_slants_non_cjk_and_keeps_cjk_upright(self):
        builder = load_builder()

        self.assertTrue(builder.should_slant_codepoint(ord("A")))
        self.assertTrue(builder.should_slant_codepoint(0x03A9))
        self.assertFalse(builder.should_slant_codepoint(0xAC00))
        self.assertFalse(builder.should_slant_codepoint(0x4E00))
        self.assertFalse(builder.should_slant_codepoint(0x3042))
        self.assertFalse(builder.should_slant_codepoint(0x30A2))
        self.assertAlmostEqual(builder.italic_slope(), 0.1763269807)


if __name__ == "__main__":
    unittest.main()
