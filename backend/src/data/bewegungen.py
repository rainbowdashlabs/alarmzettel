"""
Das Bewegungsbild für den Druck.

Jeder Ort ist ein waagerechtes Band, die Zeit läuft nach rechts, ein Aufenthalt ist ein Balken
darin und eine Fahrt eine Linie von einem Band ins andere. Die Anordnung — welche Bänder, wie
viele Reihen, welches Zeitfenster — wird hier gerechnet; das Typst-Template zeichnet sie nur.

Dieselbe Anordnung rechnet der Browser in `frontend/src/scripts/bewegungen.ts` für den
Bildschirm. Die beiden müssen übereinstimmen, sonst zeigt der Ausdruck ein anderes Bild als die
Ansicht; `tools/plan_vergleichen` hält sie aneinander.
"""

from data.planzeit import minuten as _minuten, tag as _tag
from entities.alarm import Arbeitsmappe
from entities.planung import Lauf, Planung, Schritt

STUNDE = 60


def _minute_am_tag(zeitpunkt: str, datum: str) -> int:
    return (_minuten(zeitpunkt) or 0) - (_minuten(f"{datum}T00:00") or 0)


def _von_ort(lauf: Lauf, schritt: Schritt) -> str:
    """Wo eine Fahrt losgeht, sagt der vorige Schritt."""
    if schritt.art != "fahrt":
        return schritt.ortId
    stelle = lauf.schritte.index(schritt)
    return lauf.schritte[stelle - 1].ortId if stelle > 0 else schritt.ortId


def bewegungstage(planung: Planung) -> list[str]:
    """Die Tage, an denen überhaupt etwas geplant ist."""
    tage = {_tag(schritt.von) for lauf in planung.laeufe for schritt in lauf.schritte}
    return sorted(tag for tag in tage if tag)


def _reihe_suchen(belegt: list[int], von: int, bis: int) -> int:
    """
    Der erste Platz, der zu dieser Zeit frei ist. Zwei Fahrzeuge, die nacheinander am selben Ort
    stehen, teilen sich damit eine Reihe; nur Gleichzeitiges braucht Platz übereinander.
    """
    for reihe, ende in enumerate(belegt):
        if ende <= von:
            belegt[reihe] = bis
            return reihe
    belegt.append(bis)
    return len(belegt) - 1


class _Namen:
    def __init__(self, arbeitsmappe: Arbeitsmappe) -> None:
        self.planung = arbeitsmappe.planung
        self._orte = {ort.id: ort.name for ort in self.planung.orte}
        self._personen = {person.id: person for person in self.planung.personen}
        self._lagen = {punkt.id: punkt.name for punkt in self.planung.programmpunkte}
        self._fahrzeuge = {
            fahrzeug.id: fahrzeug.funkrufname for fahrzeug in arbeitsmappe.kataloge.fahrzeuge}

    def ort(self, ort_id: str) -> str:
        return self._orte.get(ort_id, "")

    def lage(self, schritt: Schritt) -> str:
        return self._lagen.get(schritt.programmpunktId, "")

    def kette(self, lauf: Lauf) -> str:
        if lauf.fahrzeugId:
            return self._fahrzeuge.get(lauf.fahrzeugId, "")
        person = self._personen.get(lauf.personId)
        return person.name if person else ""

    def besatzung(self, schritt: Schritt) -> list[str]:
        return [self._personen[platz.personId].name if platz.personId in self._personen else ""
                for platz in schritt.besatzung]


def bewegungsbild(arbeitsmappe: Arbeitsmappe, datum: str) -> dict:
    """
    Das Bild eines Tages. Ein Ort bekommt ein Band, sobald jemand dort steht oder dorthin fährt;
    wo an diesem Tag nichts geschieht, gibt es auch kein Band.
    """
    namen = _Namen(arbeitsmappe)
    planung = arbeitsmappe.planung

    stehend = sorted(
        ((lauf, schritt, _minute_am_tag(schritt.von, datum), _minute_am_tag(schritt.bis, datum))
         for lauf in planung.laeufe for schritt in lauf.schritte
         if schritt.art == "aufenthalt" and _tag(schritt.von) == datum),
        key=lambda eintrag: eintrag[2])
    fahrten = [(lauf, schritt) for lauf in planung.laeufe for schritt in lauf.schritte
               if schritt.art == "fahrt" and _tag(schritt.von) == datum]

    beteiligt = {schritt.ortId for _, schritt, _, _ in stehend}
    for lauf, schritt in fahrten:
        beteiligt |= {_von_ort(lauf, schritt), schritt.ortId}
    reihenfolge = [ort.id for ort in planung.orte if ort.id in beteiligt and ort.id]

    belegung: dict[str, list[int]] = {ort_id: [] for ort_id in reihenfolge}
    reihen: dict[str, int] = {}
    balken = []
    for lauf, schritt, von, bis in stehend:
        if schritt.ortId not in belegung:
            continue
        reihe = _reihe_suchen(belegung[schritt.ortId], von, bis)
        reihen[schritt.id] = reihe
        balken.append({
            "laufId": lauf.id, "schrittId": schritt.id, "ortId": schritt.ortId, "reihe": reihe,
            "von": von, "bis": bis, "name": namen.kette(lauf),
            "besatzung": namen.besatzung(schritt), "lage": namen.lage(schritt),
        })

    linien = []
    for lauf, schritt in fahrten:
        stelle = lauf.schritte.index(schritt)
        abfahrt = lauf.schritte[stelle - 1] if stelle > 0 else None
        ankunft = lauf.schritte[stelle + 1] if stelle + 1 < len(lauf.schritte) else None
        linien.append({
            "laufId": lauf.id, "schrittId": schritt.id,
            "vonOrtId": _von_ort(lauf, schritt),
            "vonReihe": reihen.get(abfahrt.id, 0) if abfahrt else 0,
            "nachOrtId": schritt.ortId,
            "nachReihe": reihen.get(ankunft.id, 0) if ankunft else 0,
            "von": _minute_am_tag(schritt.von, datum), "bis": _minute_am_tag(schritt.bis, datum),
            "mittel": schritt.mittel, "name": namen.kette(lauf),
        })

    zeiten = [wert for eintrag in balken + linien for wert in (eintrag["von"], eintrag["bis"])]
    von = min(zeiten) // STUNDE * STUNDE if zeiten else 0
    bis = -(-max(zeiten) // STUNDE) * STUNDE if zeiten else STUNDE
    return {
        "datum": datum, "von": von, "bis": max(bis, von + STUNDE),
        "baender": [{"ortId": ort_id, "name": namen.ort(ort_id),
                     "reihen": max(1, len(belegung[ort_id]))}
                    for ort_id in reihenfolge],
        "balken": balken, "linien": linien,
    }


def bewegungsbilder(arbeitsmappe: Arbeitsmappe) -> list[dict]:
    return [bewegungsbild(arbeitsmappe, tag) for tag in bewegungstage(arbeitsmappe.planung)]
