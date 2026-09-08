# Bundled fonts

The slip is set in Times New Roman and Aptos, neither of which may be redistributed. These two
stand in for them and travel inside the image, so a render never depends on what happens to be
installed on the machine.

| File | Font | Stands in for | Licence |
| --- | --- | --- | --- |
| `LiberationSerif-*.ttf` | Liberation Serif 2.1.5 | Times New Roman | SIL OFL 1.1 |
| `Inter-*.ttf` | Inter 4.1 | Aptos | SIL OFL 1.1 |

Liberation Serif is metrically identical to Times New Roman, so the labels keep their widths and
their line breaks. Inter has no such relationship to Aptos; the value size was chosen by eye
against the original print and is set in one place, `WERT` in `../alarmzettel.typ`.

The Inter files are static instances cut from the upstream variable font, because Typst picks a
weight more reliably from those.

Both licences are beside the fonts. The SIL Open Font License is not the AGPL that covers the
rest of this repository, and it applies to these files alone.
