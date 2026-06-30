# AGENTS.md

## Purpose

This repository exists to produce final `SNU Sprout Sans` OTF files from three upstream `LINESeedKR` OTF masters that are supplied locally by the user.

The canonical workflow is the standalone script:

- `build_snu_sprout_sans.py`

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
- `Light`, `Medium`, `ExtraBold`: synthetic weights derived by offsetting outlines from the nearest master
- `ExtraLight`: intentionally not built because negative outline thinning damages Latin capitals
- each built weight also produces an italic companion by slanting non-CJK glyphs while keeping Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs upright
- after `cidFlatten`, every encoded glyph is renamed to a registry-neutral AGL name (`uniXXXX` / `uXXXXXX`); do not reintroduce the `Korea1.<cid>` names FontForge derives from the masters' (mislabeled) Adobe-Korea1 ROS, because macOS Core Text then resolves them through the standard Adobe-Korea1 CMap and shows wrong syllables

Do not replace this with a designspace interpolation workflow unless you first verify master compatibility across the full glyph set.

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

- keep `build_snu_sprout_sans.py` runnable end-to-end from raw OTF inputs
- keep automatic source download working unless intentionally removing that feature
- preserve the `SNU Sprout Sans` renaming step
- preserve the upright-CJK behavior in the synthetic italic outputs unless intentionally redesigning that model

If you add helper scripts, they should stay optional. The repository should still be usable with only the standalone builder plus documentation.

## Validation

After changing the build logic, at minimum:

1. Run `python3 -m unittest discover -s tests`
2. Run `fontforge -lang=py -script build_snu_sprout_sans.py Regular --upright-only`
3. Confirm the output family/style names are `SNU Sprout Sans`
4. Confirm the expected `OS/2.usWeightClass` is written

## Documentation Expectations

Keep `README.md` aligned with the actual implemented workflow, especially:

- dependency list
- required input font names
- automatic source download behavior
- output directory behavior
- the synthetic-weight caveat
- the synthetic-italic caveat

If the build behavior changes, update `README.md` and `AGENTS.md` in the same change.
