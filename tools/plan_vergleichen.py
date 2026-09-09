"""
Druckt Personenplan und Bewegungsbild, wie der Server sie rechnet, zum Vergleich mit dem Browser.

Beides wird nirgends gepflegt, sondern aus den Ketten gerechnet — einmal im Browser für die
Ansicht, einmal hier für das Blatt in der Hand. Laufen die beiden auseinander, widerspricht der
Ausdruck dem Bildschirm, und genau das soll die Ableitung ja unmöglich machen.

    python tools/plan_vergleichen.py <arbeitsmappe.json>

`./toolchain.sh ablauf-vergleichen` ruft beide Seiten auf und vergleicht sie.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from data.ablaufplan import plandaten  # noqa: E402
from entities.alarm import Arbeitsmappe  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Aufruf: python tools/plan_vergleichen.py <arbeitsmappe.json>")

mappe = Arbeitsmappe.model_validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))

daten = plandaten(mappe)

for blatt in daten["personen"]:
    for zeile in blatt["zeilen"]:
        print(" | ".join([
            "PLAN", blatt["name"], zeile["datum"], zeile["von"], zeile["bis"], zeile["art"],
            zeile["vonOrt"], zeile["ort"], zeile["lage"],
            "faehrt" if zeile["faehrt"] else "-", zeile["fahrzeug"],
        ]))

for bild in daten["bewegung"]:
    print(" | ".join(["FENSTER", bild["datum"], str(bild["von"]), str(bild["bis"])]))
    for band in bild["baender"]:
        print(" | ".join(["BAND", bild["datum"], band["name"], str(band["reihen"])]))
    for balken in bild["balken"]:
        print(" | ".join([
            "BALKEN", bild["datum"], balken["schrittId"], balken["ortId"], str(balken["reihe"]),
            str(balken["von"]), str(balken["bis"]), balken["name"],
            ",".join(balken["besatzung"]), balken["lage"],
        ]))
    for linie in bild["linien"]:
        print(" | ".join([
            "LINIE", bild["datum"], linie["schrittId"], linie["vonOrtId"], str(linie["vonReihe"]),
            linie["nachOrtId"], str(linie["nachReihe"]), str(linie["von"]), str(linie["bis"]),
            linie["mittel"], linie["name"],
        ]))
