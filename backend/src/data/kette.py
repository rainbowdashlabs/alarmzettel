"""
Was sich aus einer Kette ergibt, ohne dass es jemand pflegt: die Anfahrt zwischen zwei
Aufenthalten und der Plan einer Person.

Folgt ein Aufenthalt direkt auf einen anderen an einem anderen Ort, entsteht die Fahrt dazwischen
von selbst. Sie beginnt, wenn der Aufenthalt beginnt — wer um 7:50 aufbricht und fünf Minuten
braucht, ist um 7:55 da; deshalb ist 7:50 auch die Einsatzzeit des Alarms, der an der Lage hängt.
Eine eingetragene Fahrt bleibt möglich und hat Vorrang: sie ist der Weg über mehrere Punkte, an
denen niemand bleibt.

Dieselbe Rechnung steht im Browser in `frontend/src/scripts/ablauf.ts`; `tools/plan_vergleichen`
gibt beiden Seiten dieselben Koordinaten und hält die Ergebnisse aneinander.
"""

from dataclasses import dataclass

from data.fahrzeit import schaetzung
from data.planzeit import minuten as _minuten, verschieben
from entities.planung import Lauf, Planung, Schritt


@dataclass
class Anfahrt:
    """Die Fahrt, die zwischen zwei Aufenthalten entsteht. Sie wird nirgends gespeichert."""

    von_ort_id: str
    nach_ort_id: str
    von: str
    bis: str
    dauer: int
    mittel: str


@dataclass
class Personenschritt:
    """Ein Schritt, wie er im Plan einer Person steht — mit dem Lauf, aus dem er stammt."""

    lauf: Lauf
    schritt: Schritt
    faehrt: bool
    von_ort_id: str
    ankunft: str


def von_ort(lauf: Lauf, schritt: Schritt) -> str:
    """Wo eine Fahrt losgeht, sagt der vorige Schritt; ein Aufenthalt fängt an, wo er ist."""
    if schritt.art != "fahrt":
        return schritt.ortId
    stelle = lauf.schritte.index(schritt)
    return lauf.schritte[stelle - 1].ortId if stelle > 0 else schritt.ortId


def mittel_von(lauf: Lauf, schritt: Schritt) -> str:
    """Womit dieser Schritt zurückgelegt wird. Eine Fahrzeugkette kennt nur das Fahrzeug."""
    return "fahrzeug" if lauf.fahrzeugId else schritt.mittel


def anfahrt(lauf: Lauf, schritt: Schritt, punkte: dict) -> Anfahrt | None:
    """Die Fahrt zu diesem Aufenthalt, sofern sie entsteht."""
    if schritt.art != "aufenthalt":
        return None
    stelle = lauf.schritte.index(schritt)
    if stelle == 0:
        return None
    vorher = lauf.schritte[stelle - 1]
    if vorher.art != "aufenthalt" or vorher.ortId == schritt.ortId:
        return None
    mittel = mittel_von(lauf, schritt)
    dauer = schritt.fahrzeit or schaetzung(
        punkte.get(vorher.ortId), punkte.get(schritt.ortId), mittel) or 0
    return Anfahrt(vorher.ortId, schritt.ortId, schritt.von,
                   verschieben(schritt.von, dauer), dauer, mittel)


def ankunft(lauf: Lauf, schritt: Schritt, punkte: dict) -> str:
    """Wann jemand an dem Ort dieses Schritts steht: nach der Anfahrt, sonst sofort."""
    weg = anfahrt(lauf, schritt, punkte)
    return weg.bis if weg else schritt.von


def mitfahrer(planung: Planung, lauf: Lauf, schritt: Schritt, punkte: dict) -> list[str]:
    """Wer diese erzeugte Anfahrt mitfährt: wer laut eigenem Plan davor am Startort stand."""
    weg = anfahrt(lauf, schritt, punkte)
    if weg is None:
        return []
    dabei = [lauf.personId] if lauf.personId else []
    dabei += [platz.personId for platz in schritt.besatzung]
    return [person_id for person_id in dabei
            if any(eintrag.schritt.id == schritt.id and eintrag.von_ort_id == weg.von_ort_id
                   for eintrag in personenplan(planung, person_id, punkte))]


def fahrzeit(lauf: Lauf, schritt: Schritt, punkte: dict) -> int | None:
    """
    Die geschätzte Dauer des Weges, der zu diesem Schritt gehört: bei einer eingetragenen Fahrt
    ihre eigene, bei einem Aufenthalt die seiner erzeugten Anfahrt. Ohne Koordinaten an einem der
    beiden Orte gibt es keine Schätzung.
    """
    if schritt.art == "fahrt":
        return schaetzung(punkte.get(von_ort(lauf, schritt)), punkte.get(schritt.ortId),
                          mittel_von(lauf, schritt))
    weg = anfahrt(lauf, schritt, punkte)
    if weg is None:
        return None
    return schaetzung(punkte.get(weg.von_ort_id), punkte.get(weg.nach_ort_id), weg.mittel)


def lagen_ort(planung: Planung, programmpunkt_id: str) -> str:
    """Wo eine Lage stattfindet: dort, wo die Schritte stehen, die auf sie zeigen."""
    for lauf in planung.laeufe:
        for schritt in lauf.schritte:
            if schritt.programmpunktId == programmpunkt_id and schritt.art == "aufenthalt":
                return schritt.ortId
    return ""


def personenplan(planung: Planung, person_id: str, punkte: dict) -> list[Personenschritt]:
    """
    Alle Schritte, in deren Besatzung die Person steht, plus die ihrer eigenen Kette, nach Zeit
    sortiert. Er wird nirgends gepflegt, sondern hieraus gelesen.

    Die erzeugte Anfahrt fährt nur mit, wer vorher am Startort stand. Wer schon am Ziel wartet —
    der Mime, der auf das Fahrzeug wartet — steigt dort zu und fährt nicht mit.
    """
    eintraege: list[tuple[int, Personenschritt]] = []
    for lauf in planung.laeufe:
        eigene = lauf.personId == person_id
        for schritt in lauf.schritte:
            sitzt = next((platz for platz in schritt.besatzung
                          if platz.personId == person_id), None)
            if not eigene and sitzt is None:
                continue
            eintraege.append((_minuten(schritt.von) or 0, Personenschritt(
                lauf, schritt, bool(sitzt and sitzt.faehrt),
                von_ort(lauf, schritt), ankunft(lauf, schritt, punkte))))
    eintraege.sort(key=lambda eintrag: eintrag[0])
    plan = [eintrag for _, eintrag in eintraege]
    for stelle in range(1, len(plan)):
        weg = anfahrt(plan[stelle].lauf, plan[stelle].schritt, punkte)
        if weg and plan[stelle - 1].schritt.ortId == weg.von_ort_id:
            plan[stelle].von_ort_id = weg.von_ort_id
        else:
            plan[stelle].ankunft = plan[stelle].schritt.von
    if plan and anfahrt(plan[0].lauf, plan[0].schritt, punkte):
        plan[0].ankunft = plan[0].schritt.von
    return plan
