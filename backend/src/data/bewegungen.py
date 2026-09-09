"""
Das Bewegungsbild für den Druck.

Jeder Ort ist ein waagerechtes Band, die Zeit läuft nach rechts, ein Aufenthalt ist ein Balken
darin und eine Fahrt eine Linie von einem Band ins andere. Erzählt wird der Tag wahlweise je
Fahrzeug oder je Person; beides ist dieselbe Rechnung über **Spuren** — eine Spur ist eine Folge
von Schritten mit einem Namen. Im Fahrzeugbild ist das eine Kette, im Personenbild der Plan einer
Person, der ohnehin aus denselben Ketten entsteht.

Dieselbe Anordnung rechnet der Browser in `frontend/src/scripts/bewegungen.ts` für den
Bildschirm. Die beiden müssen übereinstimmen, sonst zeigt der Ausdruck ein anderes Bild als die
Ansicht; `tools/plan_vergleichen` hält sie aneinander.
"""

from dataclasses import dataclass, field

from data.kette import Anfahrt, anfahrt, personenplan, von_ort as _von_ort
from data.planzeit import minuten as _minuten, tag as _tag
from entities.alarm import Arbeitsmappe
from entities.planung import Lauf, Person, Planung, Schritt

STUNDE = 60

MODI = ("fahrzeuge", "personen")


def _minute_am_tag(zeitpunkt: str, datum: str) -> int:
    return (_minuten(zeitpunkt) or 0) - (_minuten(f"{datum}T00:00") or 0)


def bewegungstage(planung: Planung) -> list[str]:
    """Die Tage, an denen überhaupt etwas geplant ist."""
    tage = {_tag(schritt.von) for lauf in planung.laeufe for schritt in lauf.schritte}
    return sorted(tag for tag in tage if tag)


@dataclass
class _Spurschritt:
    """Ein Schritt, wie ihn eine Spur sieht: mit dem Ort, an dem er anfängt, und seinem Umfeld."""

    schritt: Schritt
    von_ort_id: str
    begleitung: list[str]
    anfahrt: Anfahrt | None = None
    """Die erzeugte Anfahrt, sofern diese Spur sie mitfährt."""
    ankunft: str = ""
    """Wann diese Spur an ihrem Ort steht — nach der Anfahrt, sonst mit dem Beginn."""


@dataclass
class _Spur:
    id: str
    name: str
    schritte: list[_Spurschritt] = field(default_factory=list)


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
    """
    Die Namen der Arbeitsmappe. Zeigt eine Lage auf einen Alarm, ist dessen Stichwort ihr Name:
    zweimal dasselbe zu pflegen hieße, es widersprüchlich pflegen zu können.
    """
    def __init__(self, arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> None:
        self.planung = arbeitsmappe.planung
        self.punkte = punkte or {}
        self.orte = arbeitsmappe.kataloge.alle_orte()
        self._orte = {ort.id: ort.name for ort in self.orte}
        self.personen = arbeitsmappe.kataloge.personen
        self._personen = {person.id: person for person in self.personen}
        stichwoerter = {alarm.id: alarm.stichwort for alarm in arbeitsmappe.alarme}
        self._lagen = {punkt.id: (stichwoerter.get(punkt.alarmId) or "").strip() or punkt.name
                       for punkt in self.planung.programmpunkte}
        self._fahrzeuge = {
            fahrzeug.id: fahrzeug.funkrufname for fahrzeug in arbeitsmappe.kataloge.fahrzeuge}

    def ort(self, ort_id: str) -> str:
        return self._orte.get(ort_id, "")

    def lage(self, schritt: Schritt) -> str:
        return self._lagen.get(schritt.programmpunktId, "")

    def fahrzeug(self, fahrzeug_id: str) -> str:
        return self._fahrzeuge.get(fahrzeug_id, "")

    def person(self, person_id: str) -> str:
        eintrag = self._personen.get(person_id)
        return eintrag.name if eintrag else ""

    def kette(self, lauf: Lauf) -> str:
        return self.fahrzeug(lauf.fahrzeugId) if lauf.fahrzeugId else self.person(lauf.personId)

    def besatzung(self, schritt: Schritt) -> list[str]:
        return [self.person(platz.personId) for platz in schritt.besatzung]


def _fahrzeugschritt(namen: _Namen, lauf: Lauf, schritt: Schritt) -> _Spurschritt:
    weg = anfahrt(lauf, schritt, namen.punkte)
    return _Spurschritt(schritt, _von_ort(lauf, schritt), namen.besatzung(schritt),
                        weg, weg.bis if weg else schritt.von)


def _fahrzeugspuren(namen: _Namen) -> list[_Spur]:
    """Im Fahrzeugbild ist jede Kette eine Spur — die eines Fahrzeugs wie die einer Person."""
    return [
        _Spur(lauf.id, namen.kette(lauf),
              [_fahrzeugschritt(namen, lauf, schritt) for schritt in lauf.schritte])
        for lauf in namen.planung.laeufe
    ]


def _personenspur(namen: _Namen, person: Person) -> _Spur:
    """
    Der Plan einer Person: alle Schritte, in deren Besatzung sie steht, plus die ihrer eigenen
    Kette, nach Zeit sortiert. Er wird nirgends gepflegt, sondern hieraus gelesen — deshalb kann
    das Personenbild dem Fahrzeugbild nicht widersprechen.
    """
    schritte = []
    for eintrag in personenplan(namen.planung, person.id, namen.punkte):
        begleitung = [namen.fahrzeug(eintrag.lauf.fahrzeugId)] if eintrag.lauf.fahrzeugId else []
        weg = anfahrt(eintrag.lauf, eintrag.schritt, namen.punkte)
        faehrt_mit = weg is not None and eintrag.von_ort_id == weg.von_ort_id
        schritte.append(_Spurschritt(eintrag.schritt, eintrag.von_ort_id, begleitung,
                                     weg if faehrt_mit else None, eintrag.ankunft))
    return _Spur(person.id, person.name, schritte)


def bewegungsbild(arbeitsmappe: Arbeitsmappe, datum: str, modus: str = "fahrzeuge",
                  punkte: dict | None = None) -> dict:
    """
    Das Bild eines Tages. Ein Ort bekommt ein Band, sobald jemand dort steht oder dorthin fährt;
    wo an diesem Tag nichts geschieht, gibt es auch kein Band.

    Gefahren wird auf zweierlei Weise: als eingetragene Fahrt und als die Anfahrt, die zwischen
    zwei Aufenthalten von selbst entsteht. Für das Bild ist beides dieselbe Linie — die
    eingetragene endet im nächsten Schritt, die erzeugte in ihrem eigenen, denn sie gehört zu dem
    Aufenthalt, zu dem sie führt.
    """
    namen = _Namen(arbeitsmappe, punkte)
    spuren = ([_personenspur(namen, person) for person in namen.personen]
              if modus == "personen" else _fahrzeugspuren(namen))

    stehend = sorted(
        ((spur, eintrag,
          _minute_am_tag(eintrag.ankunft, datum), _minute_am_tag(eintrag.schritt.bis, datum))
         for spur in spuren for eintrag in spur.schritte
         if eintrag.schritt.art == "aufenthalt" and _tag(eintrag.schritt.von) == datum),
        key=lambda anwesend: anwesend[2])
    fahrten = [(spur, eintrag) for spur in spuren for eintrag in spur.schritte
               if _tag(eintrag.schritt.von) == datum
               and (eintrag.schritt.art == "fahrt" or eintrag.anfahrt is not None)]

    beteiligt = {eintrag.schritt.ortId for _, eintrag, _, _ in stehend}
    for _, eintrag in fahrten:
        beteiligt |= {eintrag.anfahrt.von_ort_id if eintrag.anfahrt else eintrag.von_ort_id,
                      eintrag.schritt.ortId}
    reihenfolge = [ort.id for ort in namen.orte if ort.id and ort.id in beteiligt]

    belegung: dict[str, list[int]] = {ort_id: [] for ort_id in reihenfolge}
    reihen: dict[tuple[str, str], int] = {}
    balken = []
    for spur, eintrag, von, bis in stehend:
        if eintrag.schritt.ortId not in belegung:
            continue
        reihe = _reihe_suchen(belegung[eintrag.schritt.ortId], von, bis)
        reihen[(spur.id, eintrag.schritt.id)] = reihe
        balken.append({
            "spurId": spur.id, "schrittId": eintrag.schritt.id,
            "ortId": eintrag.schritt.ortId, "reihe": reihe, "von": von, "bis": bis,
            "name": spur.name, "begleitung": eintrag.begleitung,
            "lage": namen.lage(eintrag.schritt),
        })

    linien = []
    for spur, eintrag in fahrten:
        stelle = spur.schritte.index(eintrag)
        abfahrt = spur.schritte[stelle - 1] if stelle > 0 else None
        if eintrag.anfahrt:
            ankunft = eintrag
        else:
            ankunft = spur.schritte[stelle + 1] if stelle + 1 < len(spur.schritte) else None
        weg = eintrag.anfahrt
        linien.append({
            "spurId": spur.id, "schrittId": eintrag.schritt.id,
            "vonOrtId": weg.von_ort_id if weg else eintrag.von_ort_id,
            "vonReihe": reihen.get((spur.id, abfahrt.schritt.id), 0) if abfahrt else 0,
            "nachOrtId": eintrag.schritt.ortId,
            "nachReihe": reihen.get((spur.id, ankunft.schritt.id), 0) if ankunft else 0,
            "von": _minute_am_tag(weg.von if weg else eintrag.schritt.von, datum),
            "bis": _minute_am_tag(weg.bis if weg else eintrag.schritt.bis, datum),
            "mittel": weg.mittel if weg else eintrag.schritt.mittel, "name": spur.name,
            "begleitung": eintrag.begleitung,
        })

    zeiten = [wert for eintrag in balken + linien for wert in (eintrag["von"], eintrag["bis"])]
    von = min(zeiten) // STUNDE * STUNDE if zeiten else 0
    bis = -(-max(zeiten) // STUNDE) * STUNDE if zeiten else STUNDE
    return {
        "datum": datum, "modus": modus, "von": von, "bis": max(bis, von + STUNDE),
        "baender": [{"ortId": ort_id, "name": namen.ort(ort_id),
                     "reihen": max(1, len(belegung[ort_id]))}
                    for ort_id in reihenfolge],
        "balken": balken, "linien": linien,
    }


def bewegungsbilder(arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> list[dict]:
    """Beide Erzählweisen, jede für jeden Tag — der Bogen zeigt sie nacheinander."""
    return [bewegungsbild(arbeitsmappe, tag, modus, punkte)
            for modus in MODI
            for tag in bewegungstage(arbeitsmappe.planung)]
