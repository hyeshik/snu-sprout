# SNU Sprout 0.9.3

This release addresses missing Hangul and distorted italic text reported when
printing from Pages on macOS Tahoe to an HP Color LaserJet Pro M281fdw.
Final OTF export now rounds CFF outline and hint coordinates to integers after
weight interpolation, Hangul fitting, and italic slanting. The observed failure
pattern matches fractional coordinates; physical reprinting remains pending.

- Check every generated glyph for integer coordinates before packaging.
- Preserve glyph coverage, advance widths, GSUB features, and upright kerning.
- Recalculate italic CJK collision guards from the rounded outlines.

Validated all 16 OTFs and the 28-test suite. HarfBuzz checks confirm the five
Latin ligatures and non-colliding italic-to-Hangul layout survive.

`SNUSprout-0.9.3.zip` contains 16 OTFs and the font licenses.
