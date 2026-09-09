"""
Druckt den Personenplan, wie der Server ihn rechnet, zum Vergleich mit dem des Browsers.

Der Plan einer Person wird nirgends gepflegt, sondern aus den Ketten gerechnet — einmal im
Browser für die Ansicht, einmal hier für das Blatt in der Hand. Laufen die beiden auseinander,
widersprechen sich Bildschirm und Ausdruck, und genau das soll die Ableitung ja unmöglich machen.

    python tools/personenplan_vergleichen.py <arbeitsmappe.json>

`./toolchain.sh ablauf-vergleichen` ruft beide Seiten auf und vergleicht sie.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from data.ablaufplan import plandaten  # noqa: E402
from entities.alarm import Arbeitsmappe  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Aufruf: python tools/personenplan_vergleichen.py <arbeitsmappe.json>")

mappe = Arbeitsmappe.model_validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))

for blatt in plandaten(mappe)["personen"]:
    for zeile in blatt["zeilen"]:
        print(" | ".join([
            blatt["name"], zeile["datum"], zeile["von"], zeile["bis"], zeile["art"],
            zeile["vonOrt"], zeile["ort"], zeile["lage"],
            "faehrt" if zeile["faehrt"] else "-", zeile["fahrzeug"],
        ]))
