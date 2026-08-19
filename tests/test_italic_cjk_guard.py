import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "add_italic_cjk_guard.py"
BUILDER_PATH = ROOT / "build_snu_sprout.py"


def load_module(path: pathlib.Path, name: str):
    root = str(ROOT)
    sys.path.insert(0, root)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(root)


def load_guard():
    return load_module(SCRIPT_PATH, "add_italic_cjk_guard")


def load_builder():
    return load_module(BUILDER_PATH, "build_snu_sprout")


class ItalicCjkGuardTests(unittest.TestCase):
    def test_geometry_buckets_round_toward_more_clearance(self):
        guard = load_guard()

        self.assertEqual(guard.round_up(42, 5), 45)
        self.assertEqual(guard.round_up(-3, 5), 0)
        self.assertEqual(guard.round_down(22, 5), 20)
        self.assertEqual(guard.round_down(-3, 5), -5)

    def test_pairs_that_already_clear_keep_their_designed_spacing(self):
        guard = load_guard()

        # 'h다': the slanted glyph ends before its advance, so nothing is added.
        self.assertEqual(
            guard.guard_units(right_overhang=-15, upright_left_side_bearing=80),
            0,
        )
        # Exactly at the clearance target is still no collision.
        self.assertEqual(
            guard.guard_units(right_overhang=50, upright_left_side_bearing=80),
            0,
        )

    def test_colliding_pairs_get_a_bucket_rounded_guard(self):
        guard = load_guard()

        # 'f다' at UPM 1000: 160 unit overhang against a 78 unit side bearing.
        self.assertEqual(
            guard.guard_units(right_overhang=165, upright_left_side_bearing=75),
            120,
        )
        # 51 units required rounds up to the next 5 unit bucket.
        self.assertEqual(
            guard.guard_units(right_overhang=100, upright_left_side_bearing=79),
            55,
        )

    def test_guard_keeps_clearance_for_every_member_of_a_bucket(self):
        guard = load_guard()
        clearance = 30
        bucket = 5

        # The worst case member of a bucket has the largest real overhang and
        # the smallest real side bearing that still round into that bucket.
        for real_overhang in (155.1, 160.2, 164.9):
            for real_side_bearing in (75.0, 78.0, 79.9):
                overhang_key = guard.round_up(real_overhang, bucket)
                bearing_key = guard.round_down(real_side_bearing, bucket)
                units = guard.guard_units(
                    right_overhang=overhang_key,
                    upright_left_side_bearing=bearing_key,
                    clearance=clearance,
                    bucket_size=bucket,
                )
                gap = real_side_bearing - real_overhang + units
                self.assertGreaterEqual(gap, clearance)

    def test_glyphs_the_cmap_cannot_reach_still_pick_a_side(self):
        guard = load_guard()

        # The substituted glyphs the builder keeps are unencoded, so only their
        # names say what was sheared; a glyph with no readable name is skipped
        # rather than guessed at.
        self.assertTrue(guard.slants_in_italic("uni0066_uni0069", set()))
        self.assertTrue(guard.slants_in_italic("uni0021.locl", set()))
        self.assertFalse(guard.slants_in_italic("uniB2E4", set()))
        self.assertIsNone(guard.slants_in_italic("sprout12270", set()))
        self.assertIsNone(guard.slants_in_italic(".notdef", set()))
        self.assertTrue(guard.slants_in_italic("f.alt", {0xFF46, 0x66}))

    def test_guard_side_matches_the_builder_slant_rule(self):
        guard = load_guard()
        builder = load_builder()

        # Every glyph the builder leaves upright belongs on the upright side of
        # the guard, and every glyph it slants belongs on the other side.
        for codepoint in (
            ord("f"),
            ord("7"),
            ord("("),
            0x2044,
            0x03A9,
            ord("다"),
            ord("한"),
            0x3042,
            0x30A2,
            0x4E00,
            0xFF37,
            0x3001,
        ):
            self.assertEqual(
                guard.slants_in_italic(builder.agl_glyph_name(codepoint)),
                builder.should_slant_codepoint(codepoint),
                f"U+{codepoint:04X} is classified inconsistently",
            )

    def test_defaults_match_the_documented_build_settings(self):
        guard = load_guard()
        builder = load_builder()

        self.assertEqual(guard.DEFAULT_CLEARANCE, 30)
        self.assertEqual(guard.DEFAULT_BUCKET_SIZE, 5)
        self.assertEqual(builder.DEFAULT_GUARD_CLEARANCE, guard.DEFAULT_CLEARANCE)
        self.assertEqual(builder.DEFAULT_GUARD_BUCKET_SIZE, guard.DEFAULT_BUCKET_SIZE)


if __name__ == "__main__":
    unittest.main()
