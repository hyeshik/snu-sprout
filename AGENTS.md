# AGENTS.md

## Purpose

This repository exists to produce final `SeedKRex` OTF files from three upstream `LINESeedKR` OTF masters that are supplied locally by the user.

The canonical workflow is the standalone script:

- `build_seedkrex_from_otf.py`

Treat that script as the source of truth for the build process.

## Source of Truth

Only these inputs are required for the final build:

- `original/LINESeedKR-Th.otf`
- `original/LINESeedKR-Rg.otf`
- `original/LINESeedKR-Bd.otf`

If these files are missing, the canonical builder is allowed to download them from the configured upstream ZIP URL and place them in `original/`.

Do not commit the source fonts unless the user explicitly asks for that.

## Build Model

The repository does not rely on a true variable-font interpolation build because the upstream masters are not broadly interpolation-compatible.

Expected behavior:

- `Thin`, `Regular`, `Bold`: direct builds from the corresponding source masters
- `ExtraLight`, `Light`, `Medium`, `ExtraBold`: synthetic weights derived by offsetting outlines from the nearest master

Do not replace this with a designspace interpolation workflow unless you first verify master compatibility across the full glyph set.

## Git Expectations

Tracked files should usually be limited to:

- the end-to-end build script
- documentation
- small support files such as `.gitignore`

Do not add:

- `original/`
- `master_ufo/`
- `instance_otf/`
- temporary test output
- macOS artifact files such as `._*` or `.DS_Store`

## Editing Guidance

If you change the workflow:

- keep `build_seedkrex_from_otf.py` runnable end-to-end from raw OTF inputs
- keep automatic source download working unless intentionally removing that feature
- preserve the `SeedKRex` renaming step
- preserve the ability to use a temporary work directory
- preserve the ability to skip hinting with `--no-hint`

If you add helper scripts, they should stay optional. The repository should still be usable with only the standalone builder plus documentation.

## Validation

After changing the build logic, at minimum:

1. Run `python3 -m py_compile build_seedkrex_from_otf.py`
2. Run a smoke build for one style from the raw OTFs
3. Confirm the output family/style names are `SeedKRex`
4. Confirm the expected `OS/2.usWeightClass` is written

## Documentation Expectations

Keep `README.md` aligned with the actual implemented workflow, especially:

- dependency list
- required input font names
- automatic source download behavior
- output directory behavior
- the synthetic-weight caveat

If the build behavior changes, update `README.md` and `AGENTS.md` in the same change.
