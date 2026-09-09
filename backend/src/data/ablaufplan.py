"""
Der Ablaufplan als Druckvorlage.

Gepflegt wird nur die Kette je Fahrzeug und je Person; das Personenblatt entsteht daraus. Hier
wird dieselbe Rechnung für den Druck gemacht wie im Browser für den Bildschirm — gerechnet wird
sie einmal, damit das Blatt in der Hand und die Ansicht am Schirm nicht auseinanderlaufen
können, und das Typst-Template legt nur noch aus, was hier steht.
"""

from data.bewegungen import bewegungsbilder
from data.fahrzeit import schaetzung
from data.karten import adresstext, karten
from data.kette import anfahrt, mittel_von, mitfahrer, personenplan, von_ort as _von_ort
from data.planzeit import minuten as _minuten, tag as _datum, uhrzeit as _uhrzeit
from entities.alarm import Arbeitsmappe
from entities.planung import Lauf, Person, Planung, Schritt

RASTER = 15
"""Minuten je Zeile des Gesamtplans, wie im Raster, das der Plan bisher von Hand war."""

SPALTEN_JE_BLATT = 7
"""So viele Spalten passen quer auf ein Blatt; der Rest kommt auf das nächste."""


class Plan:
    """
    Namen und Ketten der laufenden Arbeitsmappe, in der Form, die der Druck braucht.

    Zeigt eine Lage auf einen Alarm, ist dessen Stichwort ihr Name: zweimal dasselbe zu pflegen
    hieße, es widersprüchlich pflegen zu können.
    """

    def __init__(self, arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> None:
        self.planung: Planung = arbeitsmappe.planung
        self._orte = {ort.id: ort.name for ort in arbeitsmappe.kataloge.alle_orte()}
        self.personen = arbeitsmappe.kataloge.personen
        self._personen = {person.id: person for person in self.personen}
        stichwoerter = {alarm.id: alarm.stichwort for alarm in arbeitsmappe.alarme}
        self._lagen = {punkt.id: (stichwoerter.get(punkt.alarmId) or "").strip() or punkt.name
                       for punkt in self.planung.programmpunkte}
        self._fahrzeuge = {
            fahrzeug.id: fahrzeug.funkrufname for fahrzeug in arbeitsmappe.kataloge.fahrzeuge}
        self._material = {stueck.id: stueck.name for stueck in arbeitsmappe.kataloge.material}
        self._adressen = {ort.id: ort for ort in arbeitsmappe.kataloge.alle_orte()}
        self._punkte = punkte or {}

    def ort(self, ort_id: str) -> str:
        return self._orte.get(ort_id, "")

    def lage(self, schritt: Schritt) -> str:
        return self._lagen.get(schritt.programmpunktId, "")

    def person(self, person_id: str) -> Person | None:
        return self._personen.get(person_id)

    def fahrzeug(self, fahrzeug_id: str) -> str:
        return self._fahrzeuge.get(fahrzeug_id, "")

    def name(self, lauf: Lauf) -> str:
        if lauf.fahrzeugId:
            return self.fahrzeug(lauf.fahrzeugId)
        person = self.person(lauf.personId)
        return person.name if person else ""

    def material(self, schritt: Schritt) -> list[str]:
        """Die Menge steht davor, wo es mehr als eines ist — sonst nur der Name."""
        namen = []
        for stueck in schritt.material:
            name = self._material.get(stueck.materialId, "")
            namen.append(f"{stueck.anzahl} × {name}" if name and stueck.anzahl > 1 else name)
        return namen

    def ort_mit_adresse(self, ort_id: str) -> dict | None:
        """Ein Ort, wie er auf dem Blatt steht: Name, Adresse und der Weg dorthin."""
        ort = self._adressen.get(ort_id)
        if ort is None:
            return None
        return {"name": ort.name, "adresse": adresstext(ort.adresse), **karten(ort.adresse)}

    @property
    def punkte(self) -> dict:
        return self._punkte

    def fahrzeit(self, lauf: Lauf, schritt: Schritt) -> int | None:
        """
        Wie lange die Luftlinie dauern würde — neben der geplanten Zeit auf dem Blatt. Bei einer
        eingetragenen Fahrt ist es ihre eigene, bei einem Aufenthalt die seiner Anfahrt.
        """
        if schritt.art == "fahrt":
            return schaetzung(self._punkte.get(_von_ort(lauf, schritt)),
                              self._punkte.get(schritt.ortId), mittel_von(lauf, schritt))
        weg = anfahrt(lauf, schritt, self._punkte)
        if weg is None:
            return None
        return schaetzung(self._punkte.get(weg.von_ort_id),
                          self._punkte.get(weg.nach_ort_id), weg.mittel)

    def wohin(self, schritt: Schritt) -> str:
        """Wo man ist; bei einer Fahrt, wohin sie geht."""
        ort = self.ort(schritt.ortId)
        return f"→ {ort}" if schritt.art == "fahrt" else ort


def _anfahrtszeile(plan: Plan, lauf: Lauf, schritt: Schritt,
                   besatzung: list[dict] | None = None) -> dict | None:
    """
    Die erzeugte Anfahrt als eigene Zeile. Ohne sie stünde auf dem Blatt, man sei um 7:50 schon
    da, obwohl man da erst losfährt.
    """
    weg = anfahrt(lauf, schritt, plan.punkte)
    if weg is None:
        return None
    return {
        "datum": _datum(weg.von), "von": _uhrzeit(weg.von), "bis": _uhrzeit(weg.bis),
        "art": "fahrt", "mittel": weg.mittel,
        "besatzung": besatzung if besatzung is not None else [],
        "was": f"→ {plan.ort(weg.nach_ort_id)}", "ort": plan.ort(weg.nach_ort_id), "lage": "",
        "vonOrt": plan.ort(weg.von_ort_id),
        "material": [], "notiz": "",
        "geschaetzt": plan.fahrzeit(lauf, schritt),
        "_orte": [ort_id for ort_id in (weg.von_ort_id, weg.nach_ort_id) if ort_id],
    }


def _zeile(plan: Plan, lauf: Lauf, schritt: Schritt, ankunft: str = "") -> dict:
    """Die Zeile trägt das Datum der Zeit, die auf ihr steht — das der Ankunft, nicht des Aufbruchs."""
    da = ankunft or _ankunft(plan, lauf, schritt)
    return {
        "datum": _datum(da),
        "von": _uhrzeit(da),
        "bis": _uhrzeit(schritt.bis),
        "art": schritt.art, "mittel": mittel_von(lauf, schritt),
        "was": plan.wohin(schritt), "ort": plan.ort(schritt.ortId), "lage": plan.lage(schritt),
        "vonOrt": plan.ort(_von_ort(lauf, schritt)),
        "material": [name for name in plan.material(schritt) if name],
        "notiz": schritt.notiz,
        "geschaetzt": None if schritt.art == "aufenthalt" else plan.fahrzeit(lauf, schritt),
        "_orte": [ort_id for ort_id in (_von_ort(lauf, schritt), schritt.ortId) if ort_id],
    }


def _ankunft(plan: Plan, lauf: Lauf, schritt: Schritt) -> str:
    """Auf dem Blatt beginnt ein Aufenthalt, wenn man da ist — nicht, wenn man losfährt."""
    weg = anfahrt(lauf, schritt, plan.punkte)
    return weg.bis if weg else schritt.von


def _personenblatt(plan: Plan, person: Person) -> dict:
    """
    Alle Schritte, in deren Besatzung die Person steht, plus die ihrer eigenen Kette, nach Zeit
    sortiert. Das ist der Zettel, den man morgens in die Hand drückt.
    """
    zeilen = []
    for eintrag in personenplan(plan.planung, person.id, plan.punkte):
        lauf, schritt = eintrag.lauf, eintrag.schritt
        faehrt_mit = eintrag.von_ort_id != schritt.ortId and schritt.art == "aufenthalt"
        weg = _anfahrtszeile(plan, lauf, schritt) if faehrt_mit else None
        if weg:
            zeilen.append({**weg, "fahrzeug": plan.fahrzeug(lauf.fahrzeugId),
                           "faehrt": eintrag.faehrt})
        zeilen.append({**_zeile(plan, lauf, schritt, eintrag.ankunft),
                       "fahrzeug": plan.fahrzeug(lauf.fahrzeugId),
                       "faehrt": eintrag.faehrt})
    return {"name": person.name, "anzahl": person.anzahl, "rollen": person.rollen,
            "zeilen": zeilen, "orte": _orte_des_blattes(plan, zeilen)}


def _besatzung(plan: Plan, schritt: Schritt, nur: set[str] | None = None) -> list[dict]:
    """Die Besatzung mit Namen; `nur` grenzt sie auf die ein, die die Anfahrt mitfahren."""
    eintraege = []
    for platz in schritt.besatzung:
        person = plan.person(platz.personId)
        if person and (nur is None or platz.personId in nur):
            eintraege.append({"name": person.name, "anzahl": person.anzahl,
                              "faehrt": platz.faehrt})
    return eintraege


def _fahrzeugblatt(plan: Plan, lauf: Lauf) -> dict:
    """
    Der Zettel fürs Armaturenbrett: die Kette, wie sie geplant wurde, samt Besatzung. In der
    Anfahrt steht nur, wer sie mitfährt — wer am Ziel wartet, sitzt nicht im Fahrzeug.
    """
    zeilen = []
    for schritt in lauf.schritte:
        faehrt_mit = set(mitfahrer(plan.planung, lauf, schritt, plan.punkte))
        weg = _anfahrtszeile(plan, lauf, schritt, _besatzung(plan, schritt, faehrt_mit))
        if weg:
            zeilen.append(weg)
        zeilen.append({**_zeile(plan, lauf, schritt), "besatzung": _besatzung(plan, schritt)})
    return {"name": plan.name(lauf), "zeilen": zeilen, "orte": _orte_des_blattes(plan, zeilen)}


def _orte_des_blattes(plan: Plan, zeilen: list[dict]) -> list[dict]:
    """
    Die Orte, die auf diesem Blatt vorkommen — mit Adresse, damit der Zettel für sich allein
    genügt. Wer ihn in die Hand gedrückt bekommt, hat keine zweite Liste dabei.
    """
    gesehen: list[str] = []
    for zeile in zeilen:
        for ort_id in zeile.pop("_orte", []):
            if ort_id not in gesehen:
                gesehen.append(ort_id)
    orte = [plan.ort_mit_adresse(ort_id) for ort_id in gesehen]
    return [ort for ort in orte if ort and ort["name"]]


def _spalte(plan: Plan, lauf: Lauf) -> dict:
    return {"name": plan.name(lauf) or "—",
            "art": "fahrzeug" if lauf.fahrzeugId else "person"}


def _zelle(plan: Plan, lauf: Lauf, schritt: Schritt) -> str:
    """Im Raster steht die Lage, wenn es eine gibt — sonst der Ort. So war die Tabelle gefüllt."""
    text = plan.lage(schritt) if schritt.art != "fahrt" and plan.lage(schritt) else plan.wohin(schritt)
    if lauf.fahrzeugId or schritt.art != "fahrt":
        return text
    return f"{text} ({'zu Fuß' if schritt.mittel == 'fuss' else 'eigene Anreise'})"


def _gesamtplan(plan: Plan) -> dict:
    """
    Das Raster, das der Plan vorher von Hand war: Zeit nach unten, je eine Spalte pro Kette. Es
    wird hier erzeugt statt gepflegt, und deshalb kann es nicht mehr von den Ketten abweichen.
    """
    laeufe = [lauf for lauf in plan.planung.laeufe if lauf.schritte]
    zeitpunkte = [zeit for lauf in laeufe for schritt in lauf.schritte
                  for zeit in (_minuten(schritt.von), _minuten(schritt.bis)) if zeit is not None]
    if not laeufe or not zeitpunkte:
        return {"bloecke": []}

    tage: dict[str, list[Lauf]] = {}
    for lauf in laeufe:
        for schritt in lauf.schritte:
            tage.setdefault(_datum(schritt.von), [])

    bloecke = []
    for datum in sorted(tage):
        beginn, ende = _tagesgrenzen(laeufe, datum)
        if beginn is None or ende is None:
            continue
        for teil in range(0, len(laeufe), SPALTEN_JE_BLATT):
            gruppe = laeufe[teil:teil + SPALTEN_JE_BLATT]
            zeilen = []
            for minute in range(beginn, ende, RASTER):
                zellen = [_zelle_zur_zeit(plan, lauf, datum, minute) for lauf in gruppe]
                zeilen.append({"zeit": _als_uhrzeit(minute), "zellen": zellen})
            bloecke.append({"datum": datum, "spalten": [_spalte(plan, lauf) for lauf in gruppe],
                            "zeilen": zeilen})
    return {"bloecke": bloecke}


def _tagesgrenzen(laeufe: list[Lauf], datum: str) -> tuple[int | None, int | None]:
    zeiten = [(_minuten(schritt.von), _minuten(schritt.bis))
              for lauf in laeufe for schritt in lauf.schritte if _datum(schritt.von) == datum]
    beginn = [von for von, _ in zeiten if von is not None]
    ende = [bis for _, bis in zeiten if bis is not None]
    if not beginn or not ende:
        return None, None
    return min(beginn) // RASTER * RASTER, -(-max(ende) // RASTER) * RASTER


def _als_uhrzeit(minute: int) -> str:
    innerhalb = minute % (24 * 60)
    return f"{innerhalb // 60:02d}:{innerhalb % 60:02d}"


def _zelle_zur_zeit(plan: Plan, lauf: Lauf, datum: str, minute: int) -> str:
    """
    Was in dieser Viertelstunde in dieser Spalte steht. Es zählt, was in das Fenster hineinragt,
    nicht nur was seinen Anfang überdeckt — sonst verschwände eine Fahrt von zehn Minuten, die
    zwischen zwei Rasterpunkten liegt, spurlos vom Bogen. Überlappen mehrere, gewinnt der
    längste Anteil.
    """
    beste, laengster = "", 0
    for schritt in lauf.schritte:
        if _datum(schritt.von) != datum:
            continue
        for von, bis, text in _abschnitte(plan, lauf, schritt):
            anteil = min(bis, minute + RASTER) - max(von, minute)
            if anteil > laengster:
                beste, laengster = text, anteil
    return beste


def _abschnitte(plan: Plan, lauf: Lauf, schritt: Schritt) -> list[tuple[int, int, str]]:
    """
    Ein Schritt auf der Zeitachse. Ein Aufenthalt mit erzeugter Anfahrt zerfällt in zwei Stücke:
    erst die Fahrt, dann das Dasein — sonst stünde die Lage schon im Raster, während man noch
    unterwegs ist.
    """
    von, bis = _minuten(schritt.von), _minuten(schritt.bis)
    if von is None or bis is None:
        return []
    weg = anfahrt(lauf, schritt, plan.punkte)
    da = _minuten(weg.bis) if weg else None
    if da is None or da <= von or da >= bis:
        return [(von, bis, _zelle(plan, lauf, schritt))]
    return [(von, da, f"→ {plan.ort(schritt.ortId)}"), (da, bis, _zelle(plan, lauf, schritt))]


def plandaten(arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> dict:
    """
    Personenblätter, Fahrzeugblätter und der Gesamtplan, fertig zum Auslegen.

    `punkte` sind die Koordinaten der Orte, soweit der Adressdienst sie kennt. Ohne sie fehlt auf
    den Blättern allein die geschätzte Fahrzeit.
    """
    plan = Plan(arbeitsmappe, punkte)
    return {
        "personen": [_personenblatt(plan, person) for person in plan.personen],
        "fahrzeuge": [_fahrzeugblatt(plan, lauf) for lauf in plan.planung.laeufe
                      if lauf.fahrzeugId and lauf.schritte],
        "gesamt": _gesamtplan(plan),
        "bewegung": bewegungsbilder(arbeitsmappe, punkte),
    }
