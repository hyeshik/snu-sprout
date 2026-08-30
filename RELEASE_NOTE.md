# SNU Sprout v0.8.0

SNU Sprout 0.8.0 makes the upper half of the family a continuous eight-weight
sequence. The previous ExtraBold design has been reclassified as Black, a new
ExtraBold is synthesized halfway between Bold and Black, and a new SemiBold
fills the gap between Medium and Bold. Both upright and italic variants are
included.

Every OTF reports OpenType name version `Version 0.8.0` and numeric
`head.fontRevision` value `0.8`.

## New in 0.8.0

- **New SemiBold (600):** outlines, advance widths, side bearings, and kerning
  are interpolated at two-thirds of the LINE Seed Sans KR Regular-to-Bold
  interval. It sits exactly between SNU Sprout Medium (500) and Bold (700) on
  that design axis.
- **New ExtraBold (800):** Korean and other glyphs absent from LINE Seed EN are
  generated halfway between Bold and Black, at `1.5` on the KR
  Regular-to-Bold axis. The 167 shared non-CJK glyphs instead interpolate the
  native LINE Seed EN Bold and ExtraBold outlines, metrics, and kerning at
  one-half. This keeps the English and Korean portions at the same visual step.
- **Former ExtraBold is now Black (900):** its outlines are preserved rather
  than made heavier. The shared non-CJK glyphs remain the official LINE Seed EN
  ExtraBold design, and the other glyphs remain at the Latin-calibrated `2.0`
  extrapolation point. Only their family position and weight metadata change.
- **Continuous upper-weight progression:** the resulting sequence is Medium
  500, SemiBold 600, Bold 700, ExtraBold 800, and Black 900. The new ExtraBold
  has measured Latin coverage between Bold and Black, while Black remains
  identical to the previous release's ExtraBold design.
- **Expanded flat distribution:** the archive now contains 16 OTF files plus
  `LICENSE.txt` and `LICENSE-LINESeed.txt` at its root. Specimens, documentation,
  and other project files are not included.

## Included from 0.7.0

- Intermediate weights interpolate outline size, advance width, side bearing,
  ink weight, and GPOS kerning on a single source-master axis.
- Point-compatible outlines interpolate directly. Incompatible contours use a
  fallback fitted to the same interpolated bounds and ink-weight target.
- Matching Latin point motion calibrates the upper Korean extrapolation against
  the native LINE Seed EN ExtraBold design.

## Included from earlier releases

- **OpenType-only glyphs are retained:** `fi`, `fl`, `ff`, `ffi`, and `ffl`
  ligatures, contextual `j` alternates, and Korean-localized punctuation remain
  available to their `liga`, `calt`, and `locl` lookups.
- **Synthetic italics keep CJK upright:** non-CJK glyphs are slanted 10 degrees,
  while Han, Hangul, Hiragana, Katakana, and Bopomofo glyphs stay upright. A
  generated GPOS guard prevents a slanted glyph from colliding with following
  upright CJK text without changing Latin-internal kerning.
- **Registry-neutral glyph names:** flattened CID glyphs are renamed so macOS
  Core Text and other renderers honor the font `cmap` instead of resolving them
  through the standard Adobe-Korea1 ordering.
- **Unified versions and packaging:** font name records, numeric revisions, and
  the release asset name derive from one version constant. The ZIP root contains
  only consistently named OTFs and the project and upstream licenses.

## What's in the build

The release asset is `SNUSprout-0.8.0.zip` and contains these 16 static OTFs:

- **Upright:** Thin, Light, Regular, Medium, SemiBold, Bold, ExtraBold, Black
- **Italic:** ThinItalic, LightItalic, RegularItalic, MediumItalic,
  SemiBoldItalic, BoldItalic, ExtraBoldItalic, BlackItalic

ExtraLight remains intentionally omitted because negative outline thinning
damaged Latin capital counters and lower curves.

## Upstream source

Built from the official LINE Seed Sans KR and LINE Seed Sans EN packages:

- `https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip`
- `https://seed.line.me/src/images/fonts/LINE_Seed_Sans_EN.zip`

SNU Sprout is a derivative build and does not use the reserved upstream family
name. Copyright (c) LY Corporation applies to the upstream outlines.
