# SNU Sprout 0.9.5

Improve compatibility with custom-font converters that require the conventional
PostScript glyph name for U+0020 SPACE.

- Keep the LINE Seed KR space at GID 1 with its original advance width while
  renaming it from `uni0000` to `space`.
- Remove the inherited U+0000–U+001F cmap aliases that incorrectly shared the
  same positive-width blank glyph; retain U+0020 and the separate U+00A0 glyph.
- Preserve outlines, metrics, OpenType layout, the eight-weight design, and all
  upright and italic behavior across the 16-font family.
- Credit Joongi Kim ([@achimnol](https://github.com/achimnol)), who reported
  [SNU Appendard issue #1](https://github.com/hyeshik/snu-appendard/issues/1)
  and identified the corresponding Sprout output.
- Update font metadata and the distribution package to 0.9.5.

`SNUSprout-0.9.5.zip` contains 16 OTFs and the font licenses.
