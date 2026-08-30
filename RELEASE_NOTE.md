# SNU Sprout v0.7.0

SNU Sprout is an OpenType/CFF family derived from LINE Seed Sans KR and LINE
Seed Sans. It interpolates intermediate weights and companion italics from the
Korean masters, and now uses the native English ExtraBold design where an exact
upstream weight exists.

Every OTF now uses the shared SNU family version scheme: OpenType name ID 5 is
`Version 0.7.0`, and the numeric `head.fontRevision` field is `0.7`.

## New in 0.7.0

- **Native LINE Seed EN ExtraBold:** the 167 shared non-CJK glyphs in weight 800
  now use the official EN ExtraBold outlines and advances instead of generated
  approximations. Native EN kerning is retained for pairs between those glyphs;
  mixed and Korean pairs continue on the calibrated KR axis.
- **Latin-calibrated Korean ExtraBold:** matching point motion across the KR
  Regular and Bold Latin glyphs and native EN ExtraBold places weight 800 at
  `2.0` on the Regular-to-Bold design interval. Hangul and every glyph absent
  from EN are extrapolated at that observed position, so generated Korean and
  native English share the same visual weight rather than merely following the
  numeric OS/2 weight ratio.
- **Continuous weight progression:** Light and Medium now interpolate outline
  size, advance width, side bearing, ink weight, and kerning between their
  adjacent source masters. The old nearest-master offset made the synthetic
  weights wider than the source weights on either side, especially in Latin
  text. The official EN desktop package has no Light or Medium master, so those
  weights correctly remain interpolated instead of borrowing a nearby design.
- **Master-bounded fallback outlines:** glyphs whose source contours are not
  safely point-compatible are fitted to interpolated bounds and ink weight
  instead of using FontForge's Latin counter-retention heuristic. Every Light
  and Medium glyph is checked against its adjacent masters during the build.
- **Interpolated spacing:** horizontal advances, left side bearings, and GPOS
  kerning now follow the same source-master axis as the outlines. This removes
  the two alternating width groups previously visible across the six weights.

## Included from 0.6.0

- **Unified distribution:** the release ZIP has a flat root containing only
  the 12 OTF files, `LICENSE.txt`, and `LICENSE-LINESeed.txt`.
- **Unified version metadata:** the font name record, numeric revision, and
  release asset all derive from one version constant.

## Included from 0.5.0

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
  behind the glyph, so weight interpolation, the italic slant, and the
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
encode uniquely instead of shipping a colliding one. This release reports `0.7`.

### Family name

The family was renamed from `SNU Sprout Sans` to **`SNU Sprout`** in 0.3.0, and
no backward-compatible aliases are kept. Anything that selects the old name will
not find it:

| | 0.1.2 | 0.7.0 |
|---|---|---|
| Family name | `SNU Sprout Sans` | `SNU Sprout` |
| PostScript prefix | `SNUSproutSans` | `SNUSprout` |
| Files | `SNUSproutSans-Regular.otf` | `SNUSprout-Regular.otf` |
| Release asset | `SNUSproutSans.zip` | `SNUSprout-0.7.0.zip` |

## What's in the build

The release asset is `SNUSprout-0.7.0.zip` and contains 12 static OTF files plus
the SNU Sprout and upstream LINE Seed license texts at the ZIP root:

- **Upright**: Thin, Light, Regular, Medium, Bold, ExtraBold
- **Italic**: ThinItalic, LightItalic, RegularItalic, MediumItalic, BoldItalic,
  ExtraBoldItalic

ExtraLight remains intentionally omitted, because FontForge's negative outline
thinning damaged Latin capital counters and lower curves.

## Carried over from earlier releases

- **Synthetic italics keep CJK upright**: Non-CJK glyphs are slanted 10 degrees
  while Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs stay upright.
- **CID glyph-name neutralization**: Glyphs are renamed to registry-neutral names
  after flattening, so macOS Core Text honors the font `cmap` instead of
  resolving glyphs through the standard Adobe-Korea1 CMap and showing wrong
  syllables.

## Upstream source

Built from the official LINE Seed Sans KR and LINE Seed Sans EN packages:

- `https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip`
- `https://seed.line.me/src/images/fonts/LINE_Seed_Sans_EN.zip`

SNU Sprout is a derivative build and does not use the reserved upstream family
name. Copyright (c) LY Corporation applies to the upstream outlines.
