# SNU Sprout v0.9.2

SNU Sprout 0.9.2 aligns its Hangul size, baseline, and spacing with the current
SNU font family using the reviewed Original:Appendard `2:1` fit.

## Hangul geometry

- Encoded Hangul syllables and Hangul Jamo use a `0.985927` horizontal scale,
  `0.995413` vertical scale, and `(+1.244, +3.167)` outline shift.
- Hangul advances use a `0.992827` scale so their spacing follows the fitted
  outline geometry.
- The transform runs after weight interpolation and before italic slanting,
  keeping the same Hangul fit throughout all eight upright and italic pairs.
- Han, kana, Bopomofo, CJK punctuation, LINE Seed Latin, weight interpolation,
  OpenType features, and the italic collision guard remain unchanged.
- Automated tests cover the Hangul ranges and ensure the transform does not
  extend to unrelated CJK or Latin glyphs.

## Distribution

The release asset is `SNUSprout-0.9.2.zip`. Its flat archive root contains 16
static OTF files, `LICENSE.txt`, and `LICENSE-LINESeed.txt`. Specimens, proof
PDFs, source fonts, documentation, and other project files are not included.

Every font reports `Version 0.9.2` in OpenType name ID 5 and `0.902` in
`head.fontRevision`.
