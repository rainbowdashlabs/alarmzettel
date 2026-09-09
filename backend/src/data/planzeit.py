"""
Zeitpunkte im Ablaufplan sind ISO-Zeichenketten ohne Zone — `2026-09-19T08:15`.

Gerechnet wird auf einer durchgehenden Minutenachse, damit sich zwei Zeitpunkte über Tages- und
Monatsgrenzen hinweg vergleichen und voneinander abziehen lassen.
"""

from datetime import date


def minuten(zeitpunkt: str) -> int | None:
    if len(zeitpunkt) < 16 or zeitpunkt[10] != "T":
        return None
    try:
        jahr, monat, tag = (int(teil) for teil in zeitpunkt[:10].split("-"))
        stunde, minute = int(zeitpunkt[11:13]), int(zeitpunkt[14:16])
        tage = date(jahr, monat, tag).toordinal()
    except ValueError:
        return None
    return tage * 24 * 60 + stunde * 60 + minute


def tag(zeitpunkt: str) -> str:
    return zeitpunkt[:10] if len(zeitpunkt) >= 10 else ""


def uhrzeit(zeitpunkt: str) -> str:
    return zeitpunkt[11:16] if len(zeitpunkt) >= 16 else ""


def verschieben(zeitpunkt: str, dazu: int) -> str:
    """Denselben Zeitpunkt um Minuten versetzt — auch über Mitternacht hinweg."""
    wert = minuten(zeitpunkt)
    if wert is None:
        return zeitpunkt
    tage, rest = divmod(wert + dazu, 24 * 60)
    return f"{date.fromordinal(tage).isoformat()}T{rest // 60:02d}:{rest % 60:02d}"
