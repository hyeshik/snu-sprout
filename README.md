# SNU Sprout

SNU Sprout is a LINE Seed Sans KR-derived OpenType build. The build script
downloads the LINE Seed Sans KR source package when needed, loads the three
upstream OTF masters with FontForge, synthesizes intermediate weights, and
generates upright and italic OTF instances.

The italic styles keep CJK glyphs upright and apply a synthetic 10 degree slant
to non-CJK glyphs, then add a kerning guard so slanted glyphs cannot collide
with the upright CJK glyph that follows. Intermediate weights are synthesized
from the nearest source master using a FontForge outline weight step derived
from the source master widths.

## Requirements

- FontForge with Python scripting support
- fontTools, importable from the interpreter FontForge embeds
- Python 3.10 or newer
- `make` for the convenience commands
- `zip` for package creation

On macOS with Homebrew:

```sh
brew install fontforge fonttools
```

On Ubuntu:

```sh
sudo apt-get install fontforge python3-fonttools make python3 unzip zip
```

The builder calls fontTools while FontForge is driving the script, so fontTools
must be installed for the Python that FontForge embeds rather than for whichever
`python3` comes first on `PATH`. A virtualenv or Conda environment is usually
*not* that interpreter. Check with:

```sh
fontforge -lang=py -c "import fontTools; print(fontTools.version)"
```

## Quick Start

Build the complete family:

```sh
make build
```

The first build downloads:

```text
https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip
```

The downloaded archive is stored under `vendor/downloads/`, the source OTFs are
written to `original/`, and the generated OTF files are written to
`instance_otf/`.

Run the tests:

```sh
make test
```

Build a ZIP package containing the generated OTF files and `README.md`:

```sh
make package
```

Remove generated fonts and downloaded source files:

```sh
make clean
```

## Generated Styles

The default build creates upright and italic variants for these weights:

- Thin: LINE Seed Sans KR Thin
- Light: LINE Seed Sans KR Thin plus one synthetic weight step
- Regular: LINE Seed Sans KR Regular
- Medium: LINE Seed Sans KR Regular plus one synthetic weight step
- Bold: LINE Seed Sans KR Bold
- ExtraBold: LINE Seed Sans KR Bold plus one synthetic weight step

This produces 12 OTF files in total.

## Build Details

Default build settings:

- Italic slant angle for non-CJK glyphs: `10deg`
- Synthetic weight reference glyph: `I`
- Italic collision guard ink clearance: `30` units at UPM 1000
- Italic collision guard geometry bucket: `5` units
- Font version: `0.5.0`
- Package name: `SNUSprout-0.5.0.zip`

The package name is derived from the `VERSION` constant in
`build_snu_sprout.py`, which is the single source of truth for the font version.
Bump that constant to change both the font metadata and the ZIP name.

### CID glyph-name neutralization

The upstream masters are CID-keyed and declare the `(Adobe, Korea1, 2)` ROS,
but they actually use an identity CID assignment (CID == GID) that does not
follow the real Adobe-Korea1 glyph ordering. After `cidFlatten`, FontForge
names glyphs `Korea1.<cid>`. macOS Core Text recognizes that registered ordering
and resolves such glyphs through the *standard* Adobe-Korea1 (UniKS) CMap instead
of the font `cmap`, so most syllables with a final consonant rendered as the
wrong character (for example, 겧 displayed as 쨬). The build therefore renames
every glyph to a registry-neutral name right after flattening, which makes every
renderer honor the font `cmap`. Encoded glyphs take their AGL codepoint name
(`uniXXXX` / `uXXXXXX`); the rest are named for the glyphs they are substituted
from, as described below.

### Glyphs only OpenType features reach

No codepoint maps to the `fi`, `fl`, `ff`, `ffi`, and `ffl` ligatures, the
contextual `j` alternates, or the Korean-localized punctuation. They exist only
as the output of a `liga`, `calt`, or `locl` lookup, so they are kept even
though the `cmap` cannot reach them: dropping them makes FontForge drop the
lookups that produce them, and the Latin ligatures stop forming.

Each one is named for its inputs — `uni0066_uni0069` for fi, `uni0021.locl` for
the localized exclamation mark — which keeps the name registry-neutral and
records the codepoints behind an unencoded glyph. Synthetic weighting and the
italic slant read those codepoints back, so a substituted glyph is weighted and
sheared exactly like the glyphs it replaces, and the italic collision guard
covers it as well.

### Italic-to-CJK collision guard

Slanting an outline does not change its advance width, so a sheared non-CJK
glyph can lean past its own advance and overlap the upright CJK glyph that
follows. In `f다` the italic `f` overhangs its advance by 160 units while `다`
offers only 78 units of left side bearing, leaving an 82 unit overlap.

Every italic build therefore appends a class-based GPOS pair positioning lookup
to each `kern` feature. It buckets slanted glyphs by right overhang and upright
CJK glyphs by left side bearing, then adds a positive `XAdvance` to the slanted
glyph so the pair keeps at least the configured ink clearance. Both roundings
are conservative, so the guard for a bucket is never smaller than what any
member of that bucket needs.

Properties worth knowing:

- The guard is kerning, so it inserts no space glyph and creates no line-break
  opportunity.
- Pairs that already clear are left at their designed spacing; only colliding
  pairs are widened. Latin-internal kerning is untouched.
- Upright variants get no guard, because they have no synthetic overhang.
- The slanted and upright sides are split with the same predicate the builder
  uses to decide what to shear, so the two steps cannot drift apart.
- Clearance is measured from glyph bounding boxes, not per-outline ink, so a few
  pairs whose ink never overlaps vertically are widened as well.

Applications that shape Latin and CJK as separate runs may still need an
equivalent typesetting boundary rule, because the pair never reaches the shaper.

Tune or disable the guard:

```sh
fontforge -lang=py -script build_snu_sprout.py --guard-clearance 40
fontforge -lang=py -script build_snu_sprout.py --no-italic-guard
```

It can also be applied on its own to an already generated OTF:

```sh
python3 add_italic_cjk_guard.py in.otf out.otf --clearance 30
```

The script accepts optional style names and build flags:

```sh
fontforge -lang=py -script build_snu_sprout.py Regular Bold
fontforge -lang=py -script build_snu_sprout.py --upright-only
fontforge -lang=py -script build_snu_sprout.py --italic-only
```

Use an existing local source directory without downloading:

```sh
fontforge -lang=py -script build_snu_sprout.py \
  --source-dir path/to/LINESeedKR/fonts \
  --no-download
```

Override output and slant settings:

```sh
fontforge -lang=py -script build_snu_sprout.py \
  --output-dir build/otf \
  --italic-angle 10
```

The same options can be passed through `make` variables:

```sh
make package SOURCE_DIR=path/to/LINESeedKR/fonts BUILD_FLAGS=--no-download
```

## GitHub Actions

The repository includes a GitHub Actions workflow at
`.github/workflows/build-package.yml`. It runs on pushes, pull requests, tag
pushes matching `v*`, and manual dispatches. The workflow installs FontForge,
runs the unit tests, builds all 12 OTF files, creates
`dist/SNUSprout-<version>.zip`, verifies the package, and uploads it as a
workflow artifact. When the workflow is triggered by a tag matching `v*`, it
also publishes a GitHub Release and attaches the versioned ZIP as a release
asset.

Create and push a release tag:

```sh
git tag v0.1.0
git push origin v0.1.0
```

Reusing an existing release tag is intentionally treated as an error. Use a new
version tag for each published package.

## Repository Layout

- `.github/workflows/build-package.yml`: GitHub Actions package and release workflow
- `RELEASE_NOTE.md`: notes for the current release
- `build_snu_sprout.py`: FontForge build script
- `add_italic_cjk_guard.py`: italic-to-upright-CJK collision guard, applied by the builder
- `make_distribution_zip.py`: optional helper to package built OTFs into a release ZIP
- `tests/`: unit tests for pure helper logic
- `.gitignore`: excludes source fonts and generated artifacts
- `original/`: expected location of upstream source fonts, not tracked
- `instance_otf/`: generated final fonts, not tracked
- `dist/`: generated distribution ZIPs, not tracked
- `vendor/`: downloaded source ZIPs, not tracked

## Reproducibility Notes

- The builder rewrites family/style naming to use `SNU Sprout` instead of
  the reserved upstream family name.
- Missing source OTFs are fetched automatically from the upstream LINE Seed KR
  ZIP unless `--no-download` is used.
- Italic outputs are synthetic obliques: non-CJK glyphs are slanted by the
  builder, while glyphs classified as Han, Hangul, Hiragana, Katakana, or
  Bopomofo remain upright.
- Italic outputs also carry a generated kerning guard that keeps slanted glyphs
  from colliding with the following upright CJK glyph.
- Synthetic outline weight is intentionally simple and reproducible; visual
  inspection is still recommended for `Light`, `Medium`, and `ExtraBold`.
- ExtraLight is intentionally omitted because FontForge negative outline
  thinning damaged Latin capital counters and lower curves.
