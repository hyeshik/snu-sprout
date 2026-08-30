# SNU Sprout v0.9.0

SNU Sprout 0.9.0 recalibrates the family weight axis after measuring effective
stroke width and ink coverage against SNU Appendard and SNU Edge. The release
keeps the established eight-style family, but makes Thin classification,
Light interpolation, and Korean upper-weight extrapolation follow a smoother
visual progression.

Every OTF reports OpenType name version `Version 0.9.0` and numeric
`head.fontRevision` value `0.9`.

## Weight-axis changes

- **Thin is now weight 100:** the LINE Seed Sans KR Thin outlines are unchanged,
  but `OS/2.usWeightClass` moves from 250 to the conventional Thin value 100.
  The measured Korean effective stroke width is within about 1% of SNU
  Appendard Thin, so the new metadata better describes its role in the family.
- **Light moves toward Regular:** Light remains weight 300 but is now generated
  at `0.55` of the LINE Seed Sans KR Thin-to-Regular design interval instead of
  `0.333`. Its measured effective stroke width changes from 46.6 to 56.8 for
  Latin and from 42.3 to 50.9 for the common Korean comparison set. This places
  it slightly below SNU Appendard Light and close to SNU Edge Light.
- **ExtraBold Korean extrapolation is reduced:** shared non-CJK glyphs continue
  to use one-half interpolation from native LINE Seed EN Bold to ExtraBold.
  Glyphs remaining on the KR axis now use `1.288` on the Regular-to-Bold
  interval, reducing the previous Bold-beyond excess by 10%. Measured Korean
  effective stroke width falls from 124.6 in 0.8.0 to 116.9.
- **Black Korean extrapolation is reduced:** shared non-CJK glyphs continue to
  use native LINE Seed EN ExtraBold. KR-axis glyphs now use `1.576`, likewise a
  10% reduction of the Bold-beyond excess. Measured Korean effective stroke
  width falls from 143.2 in 0.8.0 to 127.3.
- **The English upper weights remain stable:** ExtraBold and Black retain the
  same LINE Seed EN outlines, advances, side bearings, and EN-to-EN kerning as
  0.8.0. The adjustment targets the KR-derived progression without moving the
  native English endpoints.

The measurements above use A–Z, a–z, and 0–9 for Latin and the 2,479 modern
Korean syllables shared by SNU Sprout, SNU Edge, and SNU Appendard. Effective
stroke width is calculated as twice aggregate ink area divided by aggregate
outline perimeter, normalized to UPM 1000.

## Build-model changes

- OpenType metadata weights and source design-axis positions are now explicit,
  independent values. Reclassifying a style no longer changes its outlines as
  a side effect of metadata arithmetic.
- The previous Latin point-motion calibration no longer drives Korean Black.
  Light, ExtraBold, and Black use reviewed design positions directly, while
  Medium and SemiBold retain their existing one-third and two-thirds positions.
- Compatible glyph outlines still interpolate point for point. Incompatible
  outlines continue through the guarded fallback fitted to the requested
  bounds and ink target.
- Advance widths, side bearings, and GPOS kerning follow the same explicit
  source-axis positions as the outlines.

## Family contents

The release contains 16 static OpenType/CFF fonts:

- **Upright:** Thin, Light, Regular, Medium, SemiBold, Bold, ExtraBold, Black
- **Italic:** ThinItalic, LightItalic, RegularItalic, MediumItalic,
  SemiBoldItalic, BoldItalic, ExtraBoldItalic, BlackItalic

Italic styles keep Han, Hangul, Hiragana, Katakana, and Bopomofo upright while
slanting non-CJK glyphs by 10 degrees. The generated GPOS collision guard keeps
slanted glyphs from overlapping following upright CJK text.

The OpenType-only `liga`, `calt`, and `locl` glyphs remain available, including
the `fi`, `fl`, `ff`, `ffi`, and `ffl` ligatures and Korean-localized
punctuation. The fonts preserve the upstream `USE_TYPO_METRICS` behavior and
registry-neutral glyph naming introduced in earlier releases.

## Distribution

The release asset is `SNUSprout-0.9.0.zip`. Its flat archive root contains only
the 16 consistently named OTF files, `LICENSE.txt`, and
`LICENSE-LINESeed.txt`. Specimens, proof PDFs, source fonts, documentation, and
other project files are not included.

SNU Sprout is built from the official LINE Seed Sans KR and LINE Seed Sans EN
packages and does not use the reserved upstream family name. Copyright (c) LY
Corporation applies to the upstream outlines.
