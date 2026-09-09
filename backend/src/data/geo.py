"""
Von den Koordinaten einer Karte zu den amtlichen.

Der Adressdienst liefert ETRS89 / UTM 33N, und darauf rechnen Entfernung und Polar-Koordinaten.
Wer einen Punkt selbst auf der Karte setzt, gibt ihn dagegen in WGS 84 an — also wird er einmal
projiziert. Die Reihenentwicklung ist die übliche für die transversale Mercator-Projektion; auf
der Fläche einer Stadt liegt sie im Millimeterbereich.

Dieselbe Rechnung steht im Browser in `frontend/src/scripts/geo.ts`; `tools/bewegungen_pruefen`
hält beide gegen Punkte, die derselbe Berliner Dienst in beiden Systemen ausgibt.
"""

import math

A = 6378137.0
"""GRS 80, die Bezugsfläche von ETRS89."""
F = 1 / 298.257222101
K0 = 0.9996
OSTVERSATZ = 500000
MITTELMERIDIAN = 15
"""Zone 33 reicht von 12° bis 18° Ost, ihr Mittelmeridian liegt bei 15°."""


def wgs84_zu_utm33(breite: float, laenge: float) -> dict:
    e2 = F * (2 - F)
    e_strich2 = e2 / (1 - e2)
    phi = math.radians(breite)
    lam = math.radians(laenge - MITTELMERIDIAN)

    sin, cos, tan = math.sin(phi), math.cos(phi), math.tan(phi)
    n = A / math.sqrt(1 - e2 * sin**2)
    t = tan**2
    c = e_strich2 * cos**2
    a1 = lam * cos

    m = A * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
        - (35 * e2**3 / 3072) * math.sin(6 * phi))

    ostwert = K0 * n * (
        a1
        + (1 - t + c) * a1**3 / 6
        + (5 - 18 * t + t**2 + 72 * c - 58 * e_strich2) * a1**5 / 120) + OSTVERSATZ
    nordwert = K0 * (m + n * tan * (
        a1**2 / 2
        + (5 - t + 9 * c + 4 * c**2) * a1**4 / 24
        + (61 - 58 * t + t**2 + 600 * c - 330 * e_strich2) * a1**6 / 720))
    return {"ostwert": ostwert, "nordwert": nordwert}


def punkt_aus_text(text: str) -> dict | None:
    """
    Ein Koordinatenpaar, wie es die Karte hinterlässt: „52.486300, 13.521500“. Leer oder
    unlesbar heißt, dass die Adresse selbst nachgeschlagen wird.
    """
    teile = text.split(",")
    if len(teile) != 2:
        return None
    try:
        breite, laenge = (float(stueck.strip()) for stueck in teile)
    except ValueError:
        return None
    if abs(breite) > 90 or abs(laenge) > 180:
        return None
    return wgs84_zu_utm33(breite, laenge)
