"""
Compares a rendered Alarmzettel against a reference PDF, row by row.

Neither the reference document nor the data behind it belongs in this repository — both carry
real call details — so both paths are arguments:

    python tools/compare_reference.py reference.pdf rendered.pdf

Reports the horizontal and vertical offset of every word the two have in common, and the drift
per row, which is what shows whether a row is too short or too tall. Needs pdftotext.
"""

import html
import re
import subprocess
import sys
from collections import defaultdict


def words(pdf):
    xml = subprocess.run(["pdftotext", "-bbox", "-f", "1", "-l", "1", pdf, "-"],
                         capture_output=True, text=True, check=True).stdout
    pattern = r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="[\d.]+" yMax="[\d.]+">(.*?)</word>'
    return [(html.unescape(m.group(3)), float(m.group(1)), float(m.group(2)))
            for m in re.finditer(pattern, xml)]


def rows(entries, tolerance=3.0):
    grouped = defaultdict(list)
    for text, x, y in entries:
        key = next((k for k in grouped if abs(k - y) < tolerance), y)
        grouped[key].append((x, text))
    return {k: " ".join(t for _, t in sorted(v)) for k, v in sorted(grouped.items())}


def align(reference, rendered):
    keys, other = list(reference), list(rendered)
    pairs, start = [], 0
    for key in keys:
        best, index = 0.0, None
        for candidate in range(start, min(start + 4, len(other))):
            left = set(reference[key].split())
            right = set(rendered[other[candidate]].split())
            score = len(left & right) / max(1, len(left | right))
            if score > best:
                best, index = score, candidate
        if index is not None and best > 0.4:
            pairs.append((key, other[index], reference[key]))
            start = index + 1
    return pairs


def main():
    reference, rendered = rows(words(sys.argv[1])), rows(words(sys.argv[2]))
    pairs = align(reference, rendered)

    print(f"{'ref y':>7}{'render y':>10}{'dy':>7}{'Δdy':>7}  Zeile")
    print("-" * 96)
    previous = None
    for ref_y, render_y, text in pairs:
        drift = render_y - ref_y
        step = "" if previous is None else f"{drift - previous:+6.1f}"
        flag = "  <<" if previous is not None and abs(drift - previous) > 2.0 else ""
        print(f"{ref_y:7.1f}{render_y:10.1f}{drift:7.1f}{step:>7}  {text[:56]}{flag}")
        previous = drift

    ref_extent = pairs[-1][0] - pairs[0][0]
    render_extent = pairs[-1][1] - pairs[0][1]
    print("-" * 96)
    print(f"{len(pairs)} Zeilen   Höhe Referenz {ref_extent:.1f}pt   gerendert {render_extent:.1f}pt"
          f"   Abweichung {render_extent - ref_extent:+.1f}pt")


if __name__ == "__main__":
    main()
