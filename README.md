# SNU Sprout

SNU Sprout is a LINE Seed Sans KR-derived OpenType build. The build script
downloads the LINE Seed Sans KR source package when needed, loads the three
upstream OTF masters with FontForge, synthesizes intermediate weights, and
generates upright and italic OTF instances.

The italic styles keep CJK glyphs upright and apply a synthetic 10 degree slant
to non-CJK glyphs. Intermediate weights are synthesized from the nearest source
master using a FontForge outline weight step derived from the source master
widths.

## Requirements

- FontForge with Python scripting support
- Python 3.10 or newer
- `make` for the convenience commands
- `zip` for package creation

On macOS with Homebrew:

```sh
brew install fontforge
```

On Ubuntu:

```sh
sudo apt-get install fontforge make python3 unzip zip
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
- Font version: `0.3.0`
- Package name: `SNUSprout-0.3.0.zip`

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
every encoded glyph to a registry-neutral AGL name (`uniXXXX` / `uXXXXXX`) right
after flattening, which makes every renderer honor the font `cmap`.

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
- `build_snu_sprout.py`: FontForge build script
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
- Synthetic outline weight is intentionally simple and reproducible; visual
  inspection is still recommended for `Light`, `Medium`, and `ExtraBold`.
- ExtraLight is intentionally omitted because FontForge negative outline
  thinning damaged Latin capital counters and lower curves.
