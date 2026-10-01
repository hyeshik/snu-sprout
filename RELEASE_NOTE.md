# SNU Sprout 0.9.4

Apply the approved macOS system-font sizing and baseline fit to all 16 upright
and italic styles, keeping the SNU Sprout family and file names.

- Raise Hangul and Jamo by 13.5 units while retaining their original size.
- Scale Latin and other glyphs uniformly by 0.986328686, including advances,
  kerning, mark anchors, and hint zones.
- Set line metrics to 952 / −241 / 0, enable USE_TYPO_METRICS, and add a Roman
  baseline at zero while retaining safe Windows clipping bounds.
- Retain the eight-weight design, upright Hangul in italic styles, Latin
  ligatures, and italic-to-CJK collision guards.
- Preserve integer CFF coordinates and check every generated glyph before
  packaging; update font metadata and the distribution package to 0.9.4.

`SNUSprout-0.9.4.zip` contains 16 OTFs and the font licenses.
