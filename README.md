# SeedKRex Build

This repository contains a reproducible build for generating the `SeedKRex` OTF family from three upstream `LINESeedKR` source OTFs:

- `LINESeedKR-Th.otf`
- `LINESeedKR-Rg.otf`
- `LINESeedKR-Bd.otf`

The repository does not include the original source fonts in Git, but the build script can download them automatically from LINE's ZIP distribution if they are missing.

## What This Builds

The build script writes these final OTF files:

- `SeedKRex-ExtraLight.otf`
- `SeedKRex-ExtraLightItalic.otf`
- `SeedKRex-Thin.otf`
- `SeedKRex-ThinItalic.otf`
- `SeedKRex-Light.otf`
- `SeedKRex-LightItalic.otf`
- `SeedKRex-Regular.otf`
- `SeedKRex-RegularItalic.otf`
- `SeedKRex-Medium.otf`
- `SeedKRex-MediumItalic.otf`
- `SeedKRex-Bold.otf`
- `SeedKRex-BoldItalic.otf`
- `SeedKRex-ExtraBold.otf`
- `SeedKRex-ExtraBoldItalic.otf`

## Important Note

The three source masters are not broadly interpolation-compatible, so this repository does not use a true designspace interpolation pipeline for the intermediate weights.

Instead:

- `Thin`, `Regular`, and `Bold` are built directly from their corresponding source masters.
- `ExtraLight`, `Light`, `Medium`, and `ExtraBold` are synthesized by applying outline offset operations to the nearest master.
- Italic companions are synthesized from each built weight by slanting non-CJK glyphs while keeping Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs upright.

This is the implemented workflow in `build_seedkrex_from_otf.py`.

## Requirements

Use Python 3 with these packages installed:

```bash
pip install fonttools ufoLib2 ufo2ft pathops extractor psautohint
```

If your environment needs the broader fonttools extras, install:

```bash
pip install "fonttools[ufo,lxml,pathops]"
```

## Source Fonts

By default the builder looks for these files in `original/`:

```text
original/
  LINESeedKR-Th.otf
  LINESeedKR-Rg.otf
  LINESeedKR-Bd.otf
```

If any of them are missing, the builder automatically downloads:

- `https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip`

and extracts the three required OTFs into `original/`.

These files are intentionally ignored by Git.

## Build

Run the end-to-end builder:

```bash
python3 build_seedkrex_from_otf.py
```

By default it:

- reads source fonts from `original/`
- auto-downloads the upstream ZIP if the source OTFs are missing
- writes final OTFs to `instance_otf/`
- writes both upright and italic variants for each selected weight
- creates a temporary working directory for extracted UFOs
- runs `psautohint --no-zones-stems` on the generated OTFs

## Useful Options

Build into a custom output directory:

```bash
python3 build_seedkrex_from_otf.py --output-dir out
```

Build only selected styles:

```bash
python3 build_seedkrex_from_otf.py Light Medium ExtraBold
```

Build only the italic outputs for selected weights:

```bash
python3 build_seedkrex_from_otf.py Regular Bold --italic-only
```

Build only the upright outputs:

```bash
python3 build_seedkrex_from_otf.py --upright-only
```

Skip hinting:

```bash
python3 build_seedkrex_from_otf.py --no-hint
```

Disable automatic source download:

```bash
python3 build_seedkrex_from_otf.py --no-download
```

Use a different upstream ZIP URL:

```bash
python3 build_seedkrex_from_otf.py \
  --source-zip-url https://example.com/LINE_Seed_Sans_KR.zip
```

Keep the temporary working files for inspection:

```bash
python3 build_seedkrex_from_otf.py --keep-work
```

Use a fixed working directory:

```bash
python3 build_seedkrex_from_otf.py --work-dir build-work --keep-work
```

## Distribution ZIP

Create a release ZIP from the built OTFs in `instance_otf/`:

```bash
python3 make_distribution_zip.py
```

By default this writes `dist/SeedKRex-otf-YYYYMMDD.zip`.

Include `README.md` in the archive:

```bash
python3 make_distribution_zip.py --include-readme
```

Write a custom ZIP name:

```bash
python3 make_distribution_zip.py --zip-name SeedKRex-OTF.zip
```

## Repository Layout

- `build_seedkrex_from_otf.py`: standalone end-to-end builder
- `make_distribution_zip.py`: optional helper to package built OTFs into a release ZIP
- `.gitignore`: excludes source fonts and generated/intermediate artifacts
- `original/`: expected location of upstream source fonts, not tracked
- `instance_otf/`: generated final fonts, not tracked
- `dist/`: generated distribution ZIPs, not tracked
- `master_ufo/`: extracted intermediate UFOs, not tracked

## Reproducibility Notes

- The builder rewrites family/style naming to use `SeedKRex` instead of the reserved upstream family name.
- Temporary UFO extraction is done at build time, so the committed repository does not need to store generated UFOs.
- Missing source OTFs are fetched automatically from the upstream LINE Seed KR ZIP unless `--no-download` is used.
- Italic outputs are synthetic obliques: non-CJK glyphs are slanted by the builder, while glyphs classified as Han, Hangul, Hiragana, Katakana, or Bopomofo remain upright.
- `psautohint` may emit geometry warnings on synthesized extreme weights. Those do not necessarily mean the build failed, but visual inspection is still recommended for `ExtraLight` and `ExtraBold`.
