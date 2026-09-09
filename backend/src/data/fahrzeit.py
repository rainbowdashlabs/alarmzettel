"""
Die geschätzte Fahr- und Gehzeit zwischen zwei Orten.

Beide Orte haben eine Adresse, die Adresse hat Koordinaten, also ist die Luftlinie dieselbe
Rechnung wie die Polar-Koordinaten des Alarmzettels. Daraus wird eine grobe Dauer — rund 5 km/h
zu Fuß und gut 25 km/h im Stadtverkehr, wenn man den üblichen Umweg von etwa einem Viertel
gegenüber der Luftlinie einrechnet.

Die Grenze gehört dazu: die Luftlinie kennt weder Spree noch Bahndamm noch Baustelle. Zwei Orte,
die 800 m auseinanderliegen und nur über eine Brücke drei Kilometer weiter zu erreichen sind,
schätzt sie deutlich zu kurz. Sie ist ein Vorschlag, keine Vorschrift.

Dieselbe Rechnung steht im Browser in `frontend/src/scripts/ablauf.ts`; `tools/plan_vergleichen`
gibt beiden Seiten dieselben Koordinaten und hält die Ergebnisse aneinander.
"""

import math

MINUTEN_JE_KM = {"fuss": 15, "fahrzeug": 3, "eigen": 0}
"""Über die eigene Anreise wissen wir nichts, also wird sie nicht geschätzt."""


def entfernung_km(von: dict, nach: dict) -> float:
    return math.hypot(nach["ostwert"] - von["ostwert"],
                      nach["nordwert"] - von["nordwert"]) / 1000


def schaetzung(von: dict | None, nach: dict | None, mittel: str) -> int | None:
    """
    Auf fünf Minuten gerundet und nie unter fünf; ohne Koordinaten gibt es keine Schätzung.

    Gerundet wird von der Hälfte weg und nicht zur geraden Zahl hin, weil der Browser es so tut —
    eine halbe Minute Unterschied wäre eine andere Ankunftszeit auf dem Blatt als auf dem Schirm.
    """
    je_km = MINUTEN_JE_KM.get(mittel, 0)
    if not je_km or von is None or nach is None or von == nach:
        return None
    return max(5, math.floor(entfernung_km(von, nach) * je_km / 5 + 0.5) * 5)
