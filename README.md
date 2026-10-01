# SNU Sprout

Explore the complete SNU typeface collection on the [QBio Fonts website](https://qbio.io/share/fonts/).

SNU Sprout is an OpenType build derived from LINE Seed Sans KR and LINE Seed
Sans. The build script downloads both source packages when needed, loads the
three Korean OTF masters with FontForge, interpolates the complete weight
sequence at explicit design-axis positions, interpolates LINE Seed EN glyphs
for the upper weights, and generates upright and italic OTF instances.

The italic styles keep CJK glyphs upright and apply a synthetic 10 degree slant
to non-CJK glyphs, then add a kerning guard so slanted glyphs cannot collide
with the upright CJK glyph that follows. OpenType weight metadata and source
design-axis positions are independent: outline bounds, advance widths, side
bearings, and kerning are interpolated at the explicitly calibrated position.
Compatible outlines are interpolated point for point; incompatible outlines
use a master-bounded fallback fitted to the same size and weight progression.

## Vertical sizing and alignment

All main SNU Sprout fonts use the adopted macOS system-font fit. Family,
PostScript, and file names retain `SNU Sprout` / `SNUSprout` without a
`Mac` suffix. The final stage runs once after the existing design transforms,
metadata, and italic collision guard. It applies these additional transforms
at UPM 1000; positive Y moves ink upward:

| Glyph group | Uniform X/Y scale | Y shift |
|---|---:|---:|
| Hangul and Jamo, including their GSUB alternates | 1.000000000 | +13.500000000 |
| Latin and all remaining glyphs | 0.986328686 | -0.000000000 |

Both axes use the same factor, preserving the approved glyph aspect ratios.
Advances, kerning, mark anchors, and hint zones follow the corresponding scale.
The final `hhea` and `OS/2` typo metrics are **952 / −241 / 0**
(ascender / descender / line gap), with `USE_TYPO_METRICS` enabled. Windows
clipping bounds include all ink; cap/x-height metadata follows the transformed
outlines. Horizontal `BASE` entries use the Roman baseline at zero. Cmap,
GSUB substitutions and style linking are kept.

The final fit is embedded in `build_snu_sprout.py`; it needs no additional
helper script or study files.

## Printing compatibility

Final OTF export uses FontForge's `round` flag to write integer CFF outline
and hint operands after all geometry transformations. Fractional operands
correlate with missing or distorted text reported from Pages on macOS Tahoe
to an HP Color LaserJet Pro M281fdw. Integer export avoids that representation;
confirmation on that physical printer is still required. Advance widths and
the design transforms remain as specified. Built-font regression tests scan
every glyph for fractional coordinates.

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

The first complete build downloads:

```text
https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip
https://seed.line.me/src/images/fonts/LINE_Seed_Sans_EN.zip
```

The downloaded archive is stored under `vendor/downloads/`, the source OTFs are
written to `original/`, and the generated OTF files are written to
`instance_otf/`.

Run the tests:

```sh
make test
```

Build the distribution ZIP:

```sh
make distribution
```

The ZIP has no wrapper directory. Its root contains only the 16 OTF files,
`LICENSE.txt`, and `LICENSE-LINESeed.txt`; the README, release notes, and
other project files are not distributed.

Remove generated fonts and downloaded source files:

```sh
make clean
```

## Generated Styles

The default build creates upright and italic variants for these weights:

- Thin: LINE Seed Sans KR Thin, reclassified to weight 100
- Light: 55% of the Thin-to-Regular interval (weight 300)
- Regular: LINE Seed Sans KR Regular
- Medium: one-third of the Regular-to-Bold interval (weight 500)
- SemiBold: two-thirds of the Regular-to-Bold interval (weight 600)
- Bold: LINE Seed Sans KR Bold
- ExtraBold: shared non-CJK glyphs interpolate LINE Seed EN Bold-to-ExtraBold
  at one-half, while remaining glyphs continue the KR Regular-to-Bold axis at
  `1.288`
- Black: shared non-CJK glyphs use native LINE Seed EN ExtraBold, while
  remaining glyphs continue the KR Regular-to-Bold axis at `1.576`

This produces 16 OTF files in total.

The official LINE Seed EN desktop package contains Thin (250), Regular (400),
Bold (700), ExtraBold (800), and Heavy (900). It has no native Light (300) or
Medium (500), and no SemiBold (600), so those weights remain true interpolation
instances rather than borrowing a nearby EN weight. SNU Sprout deliberately
uses conventional family metadata weight 100 for its KR-derived Thin outline.
Native EN Heavy is intentionally not substituted because it is darker still.

## Build Details

Design settings before the final uniform fit described above:

- Hangul geometry: `0.985927` horizontal scale, `0.995413` vertical scale,
  `(+1.244, +3.167)` outline shift, and `0.992827` advance scale. This is the
  adopted Original:Appendard `2:1` fit; other CJK glyphs retain their source
  geometry.
- Italic slant angle for non-CJK glyphs: `10deg`
- Fallback weight-step reference glyph: `I`
- Intermediate horizontal metrics and kerning: linear interpolation by source GID
- Intermediate outline bounds: linear interpolation between source masters
- Light KR-axis position: `0.55` on the Thin-to-Regular interval
- ExtraBold KR-axis position: `1.288` on the Regular-to-Bold interval
- Black KR-axis position: `1.576` on the Regular-to-Bold interval
- ExtraBold shared non-CJK outlines, advances, side bearings, and kerning:
  one-half interpolation from LINE Seed EN Bold to ExtraBold
- Black shared non-CJK outlines, advances, side bearings, and kerning:
  native LINE Seed EN ExtraBold values (the former SNU Sprout ExtraBold design)
- Incompatible-outline fallback: nearest master, fitted to interpolated bounds
  and master-bounded ink weight
- Italic collision guard ink clearance: `30` units at UPM 1000
- Italic collision guard geometry bucket: `5` units
- Final typographic line metrics: `952 / -241 / 0`, with `USE_TYPO_METRICS` set
- PANOSE weight: `No Fit`; the upstream KR masters all report the same PANOSE
  weight, so the authoritative per-style classification is `OS/2.usWeightClass`
- Font version: `0.9.4` (`head.fontRevision == 0.904`)
- Package name: `SNUSprout-0.9.4.zip`

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
records the codepoints behind an unencoded glyph. Weight interpolation and the
italic slant read those codepoints back, so a substituted glyph is weighted and
sheared exactly like the glyphs it replaces, and the italic collision guard
covers it as well.

### Italic-to-CJK collision guard

Slanting an outline does not change its advance width, so a sheared non-CJK
glyph can lean past its own advance and overlap the upright CJK glyph that
follows. In `f다` the italic `f` overhangs its advance by 160 units while `다`
offers only 78 units of left side bearing, leaving an 82 unit overlap.

Before the final uniform fit, every italic build appends a class-based GPOS pair positioning lookup
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
  --source-dir path/to/source-fonts \
  --no-download
```

For a complete local build that directory must contain `LINESeedKR-Th.otf`,
`LINESeedKR-Rg.otf`, `LINESeedKR-Bd.otf`, `LINESeedSans_Bd.otf`, and
`LINESeedSans_XBd.otf`.

Override output and slant settings:

```sh
fontforge -lang=py -script build_snu_sprout.py \
  --output-dir build/otf \
  --italic-angle 10
```

The same options can be passed through `make` variables:

```sh
make distribution SOURCE_DIR=path/to/source-fonts BUILD_FLAGS=--no-download
```

## GitHub Actions

The repository includes a GitHub Actions workflow at
`.github/workflows/build-package.yml`. It runs on pushes, pull requests, tag
pushes matching `v*`, and manual dispatches. The workflow installs FontForge,
runs the unit tests, builds all 16 OTF files, creates
`dist/SNUSprout-<version>.zip`, verifies the package, and uploads it as a
workflow artifact. When the workflow is triggered by a tag matching `v*`, it
also publishes a GitHub Release and attaches the versioned ZIP as a release
asset.

Create and push a release tag:

```sh
git tag v0.9.4
git push origin v0.9.4
```

Reusing an existing release tag is intentionally treated as an error. Use a new
version tag for each published package.

## Repository Layout

- `.github/workflows/build-package.yml`: GitHub Actions package and release workflow
- `RELEASE_NOTE.md`: notes for the current release
- `build_snu_sprout.py`: FontForge build script
- `add_italic_cjk_guard.py`: italic-to-upright-CJK collision guard, applied by the builder
- `scripts/package_distribution.py`: creates the flat OTF-and-license release ZIP
- `LICENSE`: SNU Sprout license and upstream copyright notice
- `licenses/LINESeed.txt`: upstream LINE Seed font license
- `tests/`: unit tests for pure helper logic
- `.gitignore`: excludes source fonts and generated artifacts
- `original/`: expected location of upstream source fonts, not tracked
- `instance_otf/`: generated final fonts, not tracked
- `dist/`: generated distribution ZIPs, not tracked
- `vendor/`: downloaded source ZIPs, not tracked

## Reproducibility Notes

- The builder rewrites family/style naming to use `SNU Sprout` instead of
  the upstream family name as its primary font name. The LINE Seed OFL header
  does not declare a Reserved Font Name.
- Output fonts preserve the upstream `OS/2.fsSelection` `USE_TYPO_METRICS`
  behavior so the large fallback `hhea` box does not shift text in layouts
  that center font line boxes.
- Output fonts set `OS/2.fsType` to `0` so inherited embedding restrictions do
  not contradict the OFL.
- Missing source OTFs are fetched automatically from the upstream LINE Seed KR
  and EN ZIPs unless `--no-download` is used. ExtraBold and Black builds need
  the EN sources; builds that select neither do not.
- Italic outputs are synthetic obliques: non-CJK glyphs are slanted by the
  builder, while glyphs classified as Han, Hangul, Hiragana, Katakana, or
  Bopomofo remain upright.
- Italic outputs also carry a generated kerning guard that keeps slanted glyphs
  from colliding with the following upright CJK glyph.
- Light, Medium, and SemiBold are checked glyph by glyph to keep advance width,
  side bearing, outline bounds, and ink weight inside their adjacent masters.
  ExtraBold interpolates EN Bold-to-ExtraBold glyphs where the families overlap,
  and uses `1.288` on the KR Regular-to-Bold axis elsewhere. Black uses native
  EN ExtraBold glyphs and `1.576` on the KR axis. These independent positions
  keep the Korean progression aligned with the family weight curve instead of
  deriving Korean extrapolation from Latin point motion.
- ExtraLight is intentionally omitted because FontForge negative outline
  thinning damaged Latin capital counters and lower curves.
