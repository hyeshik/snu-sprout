import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "build_snu_sprout.py"


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
