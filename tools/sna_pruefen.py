"""
Checks the generated interrogation graph: no edge into nothing, no cycle, nothing unreachable.

    python tools/sna_pruefen.py

A node leads on either through its answers or, where the answer is typed rather than chosen,
through a single `ziel`. Both are edges, and a check that knows only one of them declares half
the graph unreachable the moment the other appears.
"""

import json
import sys
from pathlib import Path

BAUM = Path(__file__).resolve().parent.parent / "frontend" / "public" / "sna-tree.json"


def kanten(knoten: dict) -> list[str]:
    """Everywhere this node can lead, whichever way it is answered."""
    ziele = [antwort["ziel"] for antwort in knoten.get("antworten", ())]
    if knoten.get("ziel"):
        ziele.append(knoten["ziel"])
    return ziele


def main() -> None:
    baum = json.loads(BAUM.read_text(encoding="utf-8"))
    knoten = baum["knoten"]

    offen = {ziel for eintrag in knoten.values() for ziel in kanten(eintrag) if ziel not in knoten}
    if offen:
        sys.exit(f"Kanten ohne Ziel: {sorted(offen)[:5]}")

    sys.setrecursionlimit(50000)
    farbe = dict.fromkeys(knoten, 0)
    zyklen = []

    def besuchen(kennung: str) -> None:
        if farbe[kennung] == 1:
            zyklen.append(kennung)
            return
        if farbe[kennung] == 2:
            return
        farbe[kennung] = 1
        for ziel in kanten(knoten[kennung]):
            besuchen(ziel)
        farbe[kennung] = 2

    for disziplin in baum["disziplinen"]:
        besuchen(disziplin["einstieg"])

    if zyklen:
        sys.exit(f"Zyklen im Graphen: {zyklen[:5]}")
    unerreichbar = [kennung for kennung, gesehen in farbe.items() if gesehen == 0]
    if unerreichbar:
        sys.exit(f"{len(unerreichbar)} Knoten sind von keiner Disziplin aus erreichbar")

    endpunkte = sum(1 for eintrag in knoten.values() if "code" in eintrag)
    eingaben = sum(1 for eintrag in knoten.values() if "eingabe" in eintrag)
    anzahl = sum(len(kanten(eintrag)) for eintrag in knoten.values())
    print(f"{len(knoten)} Knoten, {endpunkte} Endpunkte, {eingaben} Eingabefragen, "
          f"{anzahl} Kanten, keine Zyklen, alles erreichbar")


if __name__ == "__main__":
    main()
