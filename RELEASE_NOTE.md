# SNU Sprout v0.4.0

Metadata and packaging release of SNU Sprout — a LINE Seed Sans KR-derived
OpenType/CFF family that synthesizes intermediate weights and companion italics
from three upstream masters.

The outlines, spacing, and kerning are unchanged from 0.3.0. Only the version
metadata and the build's release plumbing differ, so there is no reason to
re-test documents beyond confirming the version they pick up.

## New in 0.4.0

- **The font version is now reported honestly.** FontForge reads only the major
  and minor components of the version it is handed, so it wrote the same
  `head.fontRevision` for 0.3.0, 0.3.1, and 0.3.2. Any patch release would have
  been indistinguishable from its predecessor to font caches, font managers, and
  anything else that reads `head` rather than the name records. The builder now
  stamps `head.fontRevision` itself, and refuses a version it cannot encode
  uniquely instead of shipping a colliding one. This release reports `0.4`.
- **Tagged releases publish themselves again.** The release job downloads the
  built package but never checks out the repository, so `gh` had no git remote to
  infer the target from and every tag push died at the final step with `failed to
  run git: fatal: not a git repository`. It now passes `--repo` explicitly. The
  `v0.1.2` and `v0.3.0` releases had to be published by hand because of this.

## Included from 0.3.0

Version 0.3.0 renamed the family and added the italic collision guard. Its notes
follow, with version references updated to this release.

### Breaking change

The family was renamed from `SNU Sprout Sans` to **`SNU Sprout`**, and no
backward-compatible aliases are kept. Anything that selects the old name will not
find it:

| | 0.1.2 | 0.4.0 |
|---|---|---|
| Family name | `SNU Sprout Sans` | `SNU Sprout` |
| PostScript prefix | `SNUSproutSans` | `SNUSprout` |
| Files | `SNUSproutSans-Regular.otf` | `SNUSprout-Regular.otf` |
| Release asset | `SNUSproutSans.zip` | `SNUSprout-0.4.0.zip` |

Update CSS `font-family` declarations, document styles, and any build scripts
that reference the old names.

### Italic-to-CJK collision guard

Slanting an outline leaves its advance width alone, so a sheared non-CJK glyph
could lean past its advance into the upright CJK glyph that followed. In `f다` the
italic `f` overhung its advance by 160 units against 78 units of side bearing on
`다`, an 82 unit overlap. Every italic now carries a generated kerning lookup that
widens only the colliding pairs; `f다` goes from −82 to +38 units, while pairs
that already cleared, such as `h다`, keep the spacing they had. It is kerning, so
it inserts no space glyph and adds no line-break opportunity, and Latin-internal
kerning is untouched.

## What's in the build

The release asset is `SNUSprout-0.4.0.zip` and contains 12 static OTF files plus
`README.md`:

- **Upright**: Thin, Light, Regular, Medium, Bold, ExtraBold
- **Italic**: ThinItalic, LightItalic, RegularItalic, MediumItalic, BoldItalic,
  ExtraBoldItalic

ExtraLight remains intentionally omitted, because FontForge's negative outline
thinning damaged Latin capital counters and lower curves.

## Carried over from earlier releases

- **Synthetic italics keep CJK upright**: Non-CJK glyphs are slanted 10 degrees
  while Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs stay upright.
- **Synthetic intermediate weights**: Light, Medium, and ExtraBold are offset from
  the nearest master using a weight step derived from the master widths. Visual
  inspection is still recommended for those three.
- **CID glyph-name neutralization**: Encoded glyphs are renamed to
  registry-neutral AGL names after flattening, so macOS Core Text honors the font
  `cmap` instead of resolving glyphs through the standard Adobe-Korea1 CMap and
  showing wrong syllables.

## Upstream source

Built from LINE Seed Sans KR, fetched from
`https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip`. SNU Sprout is a
derivative build and does not use the reserved upstream family name. Copyright
(c) LY Corporation applies to the upstream outlines.
