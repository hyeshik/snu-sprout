# SNU Sprout v0.9.1

SNU Sprout 0.9.1 strengthens copyright and SIL Open Font License metadata. It
does not change glyph outlines, weight interpolation, metrics, kerning, or
family names from 0.9.0.

## Copyright and license changes

- Every OTF now carries the LY Corporation copyright and Hyeshik Chang's
  modification copyright in OpenType name ID 0.
- OpenType name ID 13 identifies the SIL Open Font License 1.1, and name ID 14
  links to the official OFL site.
- `OS/2.fsType` is normalized from the upstream value to `0` so the fonts
  advertise installable embedding consistently with the OFL.
- Documentation and font descriptions no longer call the LINE Seed family name
  reserved. The upstream LINE Seed OFL header does not declare a Reserved Font
  Name.
- Automated tests require both copyright holders and the OFL metadata while
  rejecting any invented LINE Seed RFN declaration.

The family remains `SNU Sprout` / `SNUSprout`, keeping the derivative clearly
separate from the upstream LINE Seed families even though a name change is not
mandated by an upstream RFN.

## Distribution

The release asset is `SNUSprout-0.9.1.zip`. Its flat archive root contains 16
static OTF files, `LICENSE.txt`, and `LICENSE-LINESeed.txt`. Specimens, proof
PDFs, source fonts, documentation, and other project files are not included.

Every font reports `Version 0.9.1` in OpenType name ID 5 and `0.901` in
`head.fontRevision`.
