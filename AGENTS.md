# AGENTS.md

## Purpose

This repository produces final `SNU Sprout` OTF files from three upstream
`LINESeedKR` OTF masters and the native LINE Seed EN Bold and ExtraBold OTFs.

The canonical workflow is the standalone script:

- `build_snu_sprout.py`

Treat that script as the source of truth for the build process. It calls one
helper module, `add_italic_cjk_guard.py`, while FontForge is driving it.

## Source of Truth

Only these inputs are required for the final build:

- `original/LINESeedKR-Th.otf`
- `original/LINESeedKR-Rg.otf`
- `original/LINESeedKR-Bd.otf`
- `original/LINESeedSans_Bd.otf` (needed when ExtraBold or Black is selected)
- `original/LINESeedSans_XBd.otf` (needed when ExtraBold or Black is selected)

If these files are missing, the canonical builder is allowed to download them
from the configured upstream KR and EN ZIP URLs and place them in `original/`.

fontTools must be importable from the interpreter FontForge embeds, which is
usually the system Python rather than an active virtualenv or Conda environment.

Do not commit the source fonts unless the user explicitly asks for that.

## Build Model

The repository does not rely on a designspace or variable-font build because
the upstream masters are not broadly interpolation-compatible. It does perform
guarded per-glyph interpolation between the static source masters.

Expected behavior:

- `Thin`, `Regular`, `Bold`: direct builds from the corresponding source masters;
  Thin uses conventional output metadata weight 100 without altering its source
  outline
- `Light`: weight 300 at `0.55` of the Thin-to-Regular design interval
- `Medium`: weight 500 at one-third of the Regular (400) to Bold (700) interval
- `SemiBold`: weight 600 at two-thirds of the Regular-to-Bold interval
- `ExtraBold`: shared non-CJK glyphs interpolate native LINE Seed EN Bold to
  ExtraBold at one-half; remaining glyphs extrapolate the KR Regular-to-Bold
  progression at `1.288`
- `Black`: shared non-CJK glyphs use native LINE Seed EN ExtraBold; remaining
  glyphs extrapolate the KR Regular-to-Bold progression at `1.576`
- OpenType metadata weights and source design-axis positions are separate
  values; changing one must not implicitly move the other
- compatible outlines are interpolated point for point only when topology,
  point movement, bounds, and ink area pass the builder's safety checks
- incompatible outlines start from the nearest master, use FontForge's
  `squish` counter mode, and are fitted to interpolated bounds and a
  master-bounded ink area
- advance widths, left side bearings, and GPOS kerning are interpolated by
  source GID; native EN ExtraBold metrics and EN-to-EN kerning override those
  values for grafted glyphs
- `ExtraLight`: intentionally not built because negative outline thinning damages Latin capitals
- each built weight also produces an italic companion by slanting non-CJK glyphs while keeping Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs upright
- every built weight applies the adopted Original:Appendard `2:1` affine fit
  to encoded Hangul and Hangul Jamo after weight interpolation and before
  italic slanting; other CJK glyphs retain their source geometry
- every italic build then appends a class-based GPOS pair positioning lookup to each `kern` feature so a slanted glyph cannot collide with the following upright CJK glyph; the shear leaves advance widths alone, so without it `f다` overlaps by 82 units. Split the two sides with the builder's own `slants_in_italic`, so the guard cannot drift away from the slanting rule, and keep the rounding conservative (overhangs up, side bearings down)
- after `cidFlatten`, every glyph is renamed to a registry-neutral name: encoded glyphs take their AGL codepoint name (`uniXXXX` / `uXXXXXX`) and substituted glyphs take the AGL names of their inputs (`uni0066_uni0069` for fi, `uni0021.locl`). Do not reintroduce the `Korea1.<cid>` names FontForge derives from the masters' (mislabeled) Adobe-Korea1 ROS, because macOS Core Text then resolves them through the standard Adobe-Korea1 CMap and shows wrong syllables
- keep the glyphs only `liga`, `calt`, and `locl` reach. No codepoint maps to the `fi`/`fl`/`ff`/`ffi`/`ffl` ligatures, the contextual `j` alternates, or the localized punctuation, and deleting them makes FontForge drop the lookups that produce them, which is how the Latin ligatures were lost between 0.1.2 and 0.4.0. Weighting and slanting read the codepoints back out of the names, so a substituted glyph follows the glyphs it is substituted from

Do not replace this with a designspace interpolation workflow unless you first
verify master compatibility across the full glyph set. Keep the per-glyph
bounds and ink-area guards when changing the hybrid interpolation path.

## Git Expectations

Tracked files should usually be limited to:

- the end-to-end build script
- documentation
- small support files such as `.gitignore`

Do not add:

- `original/`
- `instance_otf/`
- `dist/`
- `vendor/`
- temporary test output
- macOS artifact files such as `._*` or `.DS_Store`

## Editing Guidance

If you change the workflow:

- keep `build_snu_sprout.py` runnable end-to-end from raw OTF inputs
- keep automatic source download working unless intentionally removing that feature
- preserve the `SNU Sprout` renaming step
- keep every glyph a lookup can reach; a glyph the cmap misses is not dead weight
- preserve the upright-CJK behavior in the synthetic italic outputs unless intentionally redesigning that model
- keep the italic collision guard as kerning only: it must not insert a space glyph, must not add a line-break opportunity, and must leave non-colliding pairs at their designed spacing

If you add helper scripts, they should stay optional. The repository should still be usable with only the standalone builder plus documentation.

## Validation

After changing the build logic, at minimum:

1. Run `python3 -m unittest discover -s tests`
2. Run `fontforge -lang=py -script build_snu_sprout.py Regular --upright-only`
3. Confirm the output family/style names are `SNU Sprout`
4. Confirm the expected `OS/2.usWeightClass` is written
5. Confirm `OS/2.fsSelection` keeps bit 7 (`USE_TYPO_METRICS`) set
6. Confirm `liga`, `calt`, `locl`, and `frac` all survive into the output, and that shaping `fi fl ff ffi ffl` returns five ligature glyphs
7. Confirm ExtraBold's shared non-CJK outlines, horizontal metrics, and
   EN-to-EN kerning match the native LINE Seed EN ExtraBold source

If italic layout changed, also build one italic and confirm with a real shaper
that `f다` has a non-negative ink gap while a non-colliding pair such as `h다`
keeps the spacing it had before.

The `VERSION` constant in `build_snu_sprout.py` is the single source of truth for
the font version. The `Makefile` and the CI workflow both derive the
distribution ZIP name (`SNUSprout-<version>.zip`) from it, so bump only that
constant when releasing.

## Documentation Expectations

Keep `README.md` aligned with the actual implemented workflow, especially:

- dependency list
- required input font names
- automatic source download behavior
- native EN Bold-to-ExtraBold grafting and explicit KR-axis positions
- output directory behavior
- the hybrid weight-interpolation model
- the synthetic-italic caveat

If the build behavior changes, update `README.md` and `AGENTS.md` in the same change.
