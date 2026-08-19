# SNU Sprout v0.5.0

Outline release of SNU Sprout — a LINE Seed Sans KR-derived OpenType/CFF family
that synthesizes intermediate weights and companion italics from three upstream
masters.

The Latin ligatures and the other feature-driven glyphs are back. Every OTF
changed, so re-install rather than relying on a font cache: the version moves to
`0.5` precisely so caches and font managers can tell the two builds apart.

## New in 0.5.0

- **`fi`, `fl`, `ff`, `ffi`, and `ffl` ligate again.** The FontForge port
  deleted every glyph the `cmap` could not reach, and the five Latin ligatures
  are exactly that: `liga` substitutes them in, nothing encodes them. With the
  glyphs gone FontForge dropped the lookup that produces them, so `fi` shaped as
  two glyphs from 0.1.2 onward. The build now keeps them.
- **The contextual `j` alternates and the localized punctuation came back with
  them.** `calt` swaps `j` for a narrower form after `g`, `j`, `§`, and after
  opening brackets, and `locl` swaps 25 punctuation marks for forms drawn to sit
  with Korean text. Both lost their outputs the same way; the `calt` feature
  survived in the font as an empty shell that substituted nothing.
- **Substituted glyphs are named for what they replace.** A glyph no codepoint
  maps to is now named `uni0066_uni0069` (fi) or `uni0021.locl`, which keeps it
  clear of the `Korea1.<cid>` names that make macOS Core Text resolve glyphs
  through the standard Adobe-Korea1 CMap. The names also record the codepoints
  behind the glyph, so synthetic weighting, the italic slant, and the
  italic-to-CJK collision guard treat a ligature exactly like the glyphs it is
  built from: `fi다` now clears in italic just as `f다` does.

## Included from earlier releases

### Italic-to-CJK collision guard

Slanting an outline leaves its advance width alone, so a sheared non-CJK glyph
could lean past its advance into the upright CJK glyph that followed. In `f다` the
italic `f` overhung its advance by 160 units against 78 units of side bearing on
`다`, an 82 unit overlap. Every italic carries a generated kerning lookup that
widens only the colliding pairs; `f다` goes from −82 to +38 units, while pairs
that already cleared, such as `h다`, keep the spacing they had. It is kerning, so
it inserts no space glyph and adds no line-break opportunity, and Latin-internal
kerning is untouched.

### Honest font versions

FontForge reads only the major and minor components of the version it is handed,
so it wrote the same `head.fontRevision` for 0.3.0, 0.3.1, and 0.3.2. The builder
stamps `head.fontRevision` itself since 0.4.0, and refuses a version it cannot
encode uniquely instead of shipping a colliding one. This release reports `0.5`.

### Family name

The family was renamed from `SNU Sprout Sans` to **`SNU Sprout`** in 0.3.0, and
no backward-compatible aliases are kept. Anything that selects the old name will
not find it:

| | 0.1.2 | 0.5.0 |
|---|---|---|
| Family name | `SNU Sprout Sans` | `SNU Sprout` |
| PostScript prefix | `SNUSproutSans` | `SNUSprout` |
| Files | `SNUSproutSans-Regular.otf` | `SNUSprout-Regular.otf` |
| Release asset | `SNUSproutSans.zip` | `SNUSprout-0.5.0.zip` |

## What's in the build

The release asset is `SNUSprout-0.5.0.zip` and contains 12 static OTF files plus
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
- **CID glyph-name neutralization**: Glyphs are renamed to registry-neutral names
  after flattening, so macOS Core Text honors the font `cmap` instead of
  resolving glyphs through the standard Adobe-Korea1 CMap and showing wrong
  syllables.

## Upstream source

Built from LINE Seed Sans KR, fetched from
`https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip`. SNU Sprout is a
derivative build and does not use the reserved upstream family name. Copyright
(c) LY Corporation applies to the upstream outlines.
