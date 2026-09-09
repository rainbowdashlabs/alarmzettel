"""
Polar-Koordinaten, wie die Leitstelle sie druckt: wo die Einsatzadresse von der Wache aus liegt,
als Winkel gegen Gitternord und Luftlinie.

Die Koordinaten sind ETRS89 / UTM 33N, also reicht ebene Trigonometrie — über Berlin verzerrt die
Projektion weit unter dem Meter, auf den der Zettel rundet. Gegen einen echten Zettel geprüft:
Junker-Jörg-Straße 36 zur Archenholdstraße 21 ergibt 336,6°/2,842 km gegen gedruckte
336,6°/2,849 km.

Dieselbe Rechnung steht im Browser in `frontend/src/scripts/polar.ts`.
"""

import math


def _entfernung(meter: float) -> str:
    """Unter einem Kilometer ist die führende Null ein Leerzeichen, so druckt es das Original."""
    geschrieben = f"{meter / 1000:.3f}".replace(".", ",")
    return f" {geschrieben[1:]}" if geschrieben.startswith("0,") else geschrieben


def polar_koordinaten(von: dict, nach: dict) -> str:
    ost = nach["ostwert"] - von["ostwert"]
    nord = nach["nordwert"] - von["nordwert"]
    grad = (math.degrees(math.atan2(ost, nord)) + 360) % 360
    return f"{grad:.1f}".replace(".", ",") + f"°/{_entfernung(math.hypot(ost, nord))} km"
