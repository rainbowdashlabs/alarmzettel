"""
Turns a crew strength into the Trupp line the sheet prints.

The Trupps are filled in a fixed order and each takes a fixed number of people: the
Staffelführer and machinist together, then the Angriffs-, Wasser- and Schlauchtrupp with two
each, and finally the Melder alone. A strength that does not fill a Trupp completely still names
it, so 3 reads as SF, AT the same way 4 does.
"""

import re

TRUPPS = (("SF", 2), ("AT", 2), ("WT", 2), ("ST", 2), ("ME", 1))

_STAERKE = re.compile(r"St(?:ä|ae)rke\s*=?\s*(\d+)", re.IGNORECASE)


def trupp_text(staerke: int) -> str:
    if staerke <= 0:
        return ""
    namen: list[str] = []
    besetzt = 0
    for name, koepfe in TRUPPS:
        namen.append(name)
        besetzt += koepfe
        if besetzt >= staerke:
            break
    return f"Stärke={staerke}: " + ", ".join(namen)


def staerke_aus_text(text: str) -> int | None:
    """Reads the strength back out of a Trupp line, whatever follows it."""
    treffer = _STAERKE.search(text or "")
    return int(treffer.group(1)) if treffer else None
