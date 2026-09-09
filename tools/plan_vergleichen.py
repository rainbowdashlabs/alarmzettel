"""
Druckt den Personenplan, wie der Server ihn rechnet, zum Vergleich mit dem Browser.

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
from data.alarmplan import einsaetze  # noqa: E402
from entities.alarm import Arbeitsmappe  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Aufruf: python tools/plan_vergleichen.py <arbeitsmappe.json>")

mappe = Arbeitsmappe.model_validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))

# Die Koordinaten stehen daneben und nicht im Adressdienst: verglichen wird die Rechnung, nicht
# das Nachschlagen. Beide Seiten bekommen dieselben Zahlen.
punkte = json.loads((Path(sys.argv[1]).parent / "punkte.json").read_text(encoding="utf-8"))

daten = plandaten(mappe, punkte)

for blatt in daten["personen"]:
    for zeile in blatt["zeilen"]:
        print(" | ".join([
            "PLAN", blatt["name"], zeile["datum"], zeile["von"], zeile["bis"], zeile["art"],
            zeile["vonOrt"], zeile["ort"], zeile["lage"],
            "faehrt" if zeile["faehrt"] else "-", zeile["fahrzeug"],
            str(zeile["geschaetzt"] if zeile["geschaetzt"] is not None else "-"),
        ]))

for einsatz in einsaetze(mappe, punkte):
    print(" | ".join([
        "EINSATZ", einsatz["lage"], str(einsatz["nummer"]), einsatz["ortId"],
        einsatz["von"], einsatz["da"], einsatz["bis"],
        ",".join(f"{eintrag['name']}{'' if eintrag['aufgebot'] else '*'}"
                 for eintrag in einsatz["beteiligte"]),
    ]))
