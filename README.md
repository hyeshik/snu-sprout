# SeedKRex Build

This repository contains a reproducible build for generating the `SeedKRex` OTF family from three upstream `LINESeedKR` source OTFs:

- `LINESeedKR-Th.otf`
- `LINESeedKR-Rg.otf`
- `LINESeedKR-Bd.otf`

The repository does not include the original source fonts in Git, but the build script can download them automatically from LINE's ZIP distribution if they are missing.

## What This Builds

The build script writes these final OTF files:

- `SeedKRex-ExtraLight.otf`
- `SeedKRex-Thin.otf`
- `SeedKRex-Light.otf`
- `SeedKRex-Regular.otf`
- `SeedKRex-Medium.otf`
- `SeedKRex-Bold.otf`
- `SeedKRex-ExtraBold.otf`

## Important Note

The three source masters are not broadly interpolation-compatible, so this repository does not use a true designspace interpolation pipeline for the intermediate weights.

Instead:

- `Thin`, `Regular`, and `Bold` are built directly from their corresponding source masters.
- `ExtraLight`, `Light`, `Medium`, and `ExtraBold` are synthesized by applying outline offset operations to the nearest master.

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

## Repository Layout

- `build_seedkrex_from_otf.py`: standalone end-to-end builder
- `.gitignore`: excludes source fonts and generated/intermediate artifacts
- `original/`: expected location of upstream source fonts, not tracked
- `instance_otf/`: generated final fonts, not tracked
- `master_ufo/`: extracted intermediate UFOs, not tracked

## Reproducibility Notes

- The builder rewrites family/style naming to use `SeedKRex` instead of the reserved upstream family name.
- Temporary UFO extraction is done at build time, so the committed repository does not need to store generated UFOs.
- Missing source OTFs are fetched automatically from the upstream LINE Seed KR ZIP unless `--no-download` is used.
- `psautohint` may emit geometry warnings on synthesized extreme weights. Those do not necessarily mean the build failed, but visual inspection is still recommended for `ExtraLight` and `ExtraBold`.
