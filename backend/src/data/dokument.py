"""
The shared working set as a set of facts that merge without losing anything.

A document is held as a flat map of path to value, each carrying the revision it was written at.
Merging two versions means taking, for every path, the value written later — so two people
editing different fields of the same Alarm both keep their change, and only writing the very same
field at the very same moment lets one win.

Paths carry the identity of what they describe:

    alarme / <alarmId> / stichwort
    alarme / <alarmId> / anfahrtsadresse / strasse
    alarme / <alarmId> / hinweise / <eintragId> / text
    alarme / <alarmId> / einsatzmittel / <gruppeId> / fahrzeuge / <fahrzeugId> / funkrufname
    kataloge / stichwoerter / <wert>

The separator is the unit separator rather than a dot or a slash, because catalogue entries are
themselves part of the path and contain both — "Allergie / Kontakt mit giftigen Tieren" is a
Stichwort, not two path segments.

Deleting writes a tombstone rather than dropping the path, because a client that has not heard
about the deletion would otherwise send the entry back and resurrect it.
"""

from typing import Any

TRENNER = "\x1f"


def _pfad(*teile: str) -> str:
    return TRENNER.join(teile)


def teile(pfad: str) -> list[str]:
    return pfad.split(TRENNER)


def _adresse_felder(basis: str, adresse: dict) -> dict[str, Any]:
    return {_pfad(basis, feld): adresse.get(feld, "")
            for feld in ("strasse", "hnr", "objekt", "plz", "ort")}


FAHRZEUGFELDER = ("funkrufname", "staerke", "ezp", "status", "plaetze", "fuehrerschein")

PLANUNGSLISTEN = ("rollen", "fahrerlaubnisse")

# Jede Liste des Plans mit den Feldern, die als Pfad je Eintrag geschrieben werden. Die
# geschachtelten Teile — Adresse, Verfügbarkeit, Schritte, Besatzung — hängen darunter.
PLANUNGSEINTRAEGE = {
    "tage": ("datum", "name"),
    "orte": ("name",),
    "personen": ("name", "anzahl"),
    "programmpunkte": ("name", "ortId", "alarmId"),
    "laeufe": ("fahrzeugId", "personId"),
}

SCHRITTFELDER = ("art", "mittel", "von", "bis", "ortId", "programmpunktId", "aufgebot")

VORGABEN: dict[str, Any] = {"aufgebot": True, "faehrt": False}
"""
Was ein Feld bedeutet, das eine ältere Arbeitsmappe noch gar nicht kannte. Für Text ist das der
leere String; ein Wahrheitswert braucht seine eigene Vorgabe, sonst käme ein leerer String zurück,
den das Modell nicht als Ja oder Nein lesen kann.
"""


def _eintragsfelder(basis: str, eintrag: dict, felder, stelle: int) -> dict[str, Any]:
    werte: dict[str, Any] = {_pfad(basis, "sortierung"): eintrag.get("sortierung", float(stelle))}
    for feld in felder:
        wert = eintrag.get(feld)
        werte[_pfad(basis, feld)] = VORGABEN.get(feld, "") if wert is None else wert
    return werte


def _planungsfelder(planung: dict) -> dict[str, Any]:
    """
    Den Plan flach machen. Die Ketten sind das Tiefste im Dokument — Lauf, Schritt, Besatzung —
    und jede Ebene trägt ihre eigene id, damit zwei Leute an verschiedenen Schritten desselben
    Laufs arbeiten können, ohne sich zu überschreiben.
    """
    werte: dict[str, Any] = {_pfad("planung", "aktiv"): planung.get("aktiv", False)}
    for liste in PLANUNGSLISTEN:
        for wert in planung.get(liste, []):
            werte[_pfad("planung", liste, wert)] = True

    for liste, felder in PLANUNGSEINTRAEGE.items():
        for stelle, eintrag in enumerate(planung.get(liste, [])):
            basis = _pfad("planung", liste, eintrag["id"])
            werte.update(_eintragsfelder(basis, eintrag, felder, stelle))

            if liste == "orte":
                werte.update(_adresse_felder(_pfad(basis, "adresse"), eintrag.get("adresse") or {}))
            elif liste == "personen":
                for satz in ("rollen", "fahrerlaubnis"):
                    for wert in eintrag.get(satz, []):
                        werte[_pfad(basis, satz, wert)] = True
                for platz, fenster in enumerate(eintrag.get("verfuegbar", [])):
                    werte.update(_eintragsfelder(_pfad(basis, "verfuegbar", fenster["id"]),
                                                 fenster, ("von", "bis"), platz))
            elif liste == "laeufe":
                for platz, schritt in enumerate(eintrag.get("schritte", [])):
                    sbasis = _pfad(basis, "schritte", schritt["id"])
                    werte.update(_eintragsfelder(sbasis, schritt, SCHRITTFELDER, platz))
                    for rang, sitzt in enumerate(schritt.get("besatzung", [])):
                        werte.update(_eintragsfelder(_pfad(sbasis, "besatzung", sitzt["id"]),
                                                     sitzt, ("personId", "faehrt"), rang))
    return werte


def flach(arbeitsmappe: dict) -> dict[str, Any]:
    """Turns a working set into the flat map the merge operates on."""
    werte: dict[str, Any] = {}

    for reihe, alarm in enumerate(arbeitsmappe.get("alarme", [])):
        basis = _pfad("alarme", alarm["id"])
        werte[_pfad(basis, "sortierung")] = alarm.get("sortierung", float(reihe))

        for feld, wert in alarm.items():
            if feld in ("id", "sortierung", "anfahrtsadresse", "einsatzadresse", "karte",
                        "hinweise", "einsatzmittel"):
                continue
            werte[_pfad(basis, feld)] = wert

        for name in ("anfahrtsadresse", "einsatzadresse"):
            werte.update(_adresse_felder(_pfad(basis, name), alarm.get(name) or {}))
        for feld, wert in (alarm.get("karte") or {}).items():
            werte[_pfad(basis, "karte", feld)] = wert

        for stelle, hinweis in enumerate(alarm.get("hinweise", [])):
            hbasis = _pfad(basis, "hinweise", hinweis["id"])
            werte[_pfad(hbasis, "sortierung")] = hinweis.get("sortierung", float(stelle))
            for feld, wert in hinweis.items():
                if feld not in ("id", "sortierung"):
                    werte[_pfad(hbasis, feld)] = wert

        for stelle, gruppe in enumerate(alarm.get("einsatzmittel", [])):
            gbasis = _pfad(basis, "einsatzmittel", gruppe["id"])
            werte[_pfad(gbasis, "sortierung")] = gruppe.get("sortierung", float(stelle))
            werte[_pfad(gbasis, "gruppe")] = gruppe.get("gruppe", "")
            for platz, fahrzeug in enumerate(gruppe.get("fahrzeuge", [])):
                fbasis = _pfad(gbasis, "fahrzeuge", fahrzeug["id"])
                werte[_pfad(fbasis, "sortierung")] = fahrzeug.get("sortierung", float(platz))
                for feld, wert in fahrzeug.items():
                    if feld not in ("id", "sortierung"):
                        werte[_pfad(fbasis, feld)] = wert

    kataloge = arbeitsmappe.get("kataloge") or {}
    werte[_pfad("kataloge", "arbeitsgruppe")] = kataloge.get("arbeitsgruppe", "")
    werte.update(_adresse_felder(_pfad("kataloge", "wache"), kataloge.get("wache") or {}))
    # Status and Trupp are words and nothing else, so the word is its own key. Stichwörter and
    # vehicles are pointed at by the Alarme, so they are keyed by an id that a rename survives.
    for liste in ("status", "trupp"):
        for wert in kataloge.get(liste, []):
            werte[_pfad("kataloge", liste, wert)] = True
    for eintrag in kataloge.get("stichwoerter", []):
        # A Stichwort was a bare string before the catalogue had ids. Reading one as its own id
        # keeps an old file working; the browser gives it a real one the next time it saves.
        eintrag = {"id": eintrag, "text": eintrag} if isinstance(eintrag, str) else eintrag
        kennung = eintrag.get("id") or eintrag.get("text", "")
        werte[_pfad("kataloge", "stichwoerter", kennung, "text")] = eintrag.get("text", "")
    for vorlage in kataloge.get("fahrzeuge", []):
        vbasis = _pfad("kataloge", "fahrzeuge", vorlage.get("id") or vorlage.get("funkrufname", ""))
        for feld in FAHRZEUGFELDER:
            werte[_pfad(vbasis, feld)] = vorlage.get(feld, "")

    werte.update(_planungsfelder(arbeitsmappe.get("planung") or {}))
    return werte


def sortierung_setzen(arbeitsmappe: dict) -> dict:
    """
    Numbers every list by its current position.

    A working set arriving from a file or an import carries its order in the order of its lists,
    not in a sort key — the key is zero everywhere. Left alone, the entries would come back out
    ordered by their random ids, which is how a set of Hinweise silently changes places.
    """
    for stelle, alarm in enumerate(arbeitsmappe.get("alarme", [])):
        alarm["sortierung"] = float(stelle)
        for platz, hinweis in enumerate(alarm.get("hinweise", [])):
            hinweis["sortierung"] = float(platz)
        for platz, gruppe in enumerate(alarm.get("einsatzmittel", [])):
            gruppe["sortierung"] = float(platz)
            for rang, fahrzeug in enumerate(gruppe.get("fahrzeuge", [])):
                fahrzeug["sortierung"] = float(rang)
    return arbeitsmappe


def _planung_lesen(planung: dict, rest: list[str], wert: Any) -> None:
    """
    Einen Pfad des Plans zurück in die geschachtelte Form legen. Die Ebenen unter einem Eintrag
    tragen ein `_` im Namen, solange sie noch Wörterbücher nach id sind; `rund` macht am Ende
    sortierte Listen daraus.
    """
    if not rest:
        return
    if len(rest) == 1:
        planung[rest[0]] = wert
        return
    if rest[0] in PLANUNGSLISTEN:
        planung[rest[0]].append(rest[1])
        return
    if rest[0] not in PLANUNGSEINTRAEGE:
        return

    eintrag = planung[rest[0]].setdefault(rest[1], {"id": rest[1]})
    tiefer = rest[2:]
    if len(tiefer) == 1:
        eintrag[tiefer[0]] = wert
    elif tiefer[0] == "adresse" and len(tiefer) == 2:
        eintrag.setdefault("adresse", {})[tiefer[1]] = wert
    elif tiefer[0] in ("rollen", "fahrerlaubnis") and len(tiefer) == 2:
        eintrag.setdefault(tiefer[0], []).append(tiefer[1])
    elif tiefer[0] == "verfuegbar" and len(tiefer) == 3:
        fenster = eintrag.setdefault("_verfuegbar", {}).setdefault(tiefer[1], {"id": tiefer[1]})
        fenster[tiefer[2]] = wert
    elif tiefer[0] == "schritte" and len(tiefer) >= 3:
        schritt = eintrag.setdefault("_schritte", {}).setdefault(tiefer[1], {"id": tiefer[1]})
        if len(tiefer) == 3:
            schritt[tiefer[2]] = wert
        elif tiefer[2] == "besatzung" and len(tiefer) == 5:
            schritt.setdefault("_besatzung", {}).setdefault(
                tiefer[3], {"id": tiefer[3]})[tiefer[4]] = wert


def _leerer_alarm(kennung: str) -> dict:
    return {"id": kennung, "anfahrtsadresse": {}, "einsatzadresse": {}, "karte": {},
            "hinweise": [], "einsatzmittel": []}


def rund(werte: dict[str, Any]) -> dict:
    """Builds the working set back out of the flat map, in sort-key order."""
    alarme: dict[str, dict] = {}
    kataloge: dict[str, Any] = {"stichwoerter": {}, "status": [], "trupp": [], "fahrzeuge": {},
                                "arbeitsgruppe": "", "wache": {}}
    planung: dict[str, Any] = {"aktiv": False, "rollen": [], "fahrerlaubnisse": [],
                               **{liste: {} for liste in PLANUNGSEINTRAEGE}}

    for pfad, wert in werte.items():
        stueck = teile(pfad)
        if stueck[0] == "planung":
            _planung_lesen(planung, stueck[1:], wert)
            continue
        if stueck[0] == "kataloge" and len(stueck) == 2:
            kataloge[stueck[1]] = wert
            continue
        if stueck[0] == "kataloge" and len(stueck) >= 3:
            if stueck[1] == "wache" and len(stueck) == 3:
                kataloge["wache"][stueck[2]] = wert
            elif stueck[1] in ("status", "trupp"):
                kataloge[stueck[1]].append(stueck[2])
            elif stueck[1] == "stichwoerter" and len(stueck) == 4:
                kataloge["stichwoerter"].setdefault(stueck[2], {"id": stueck[2]})[stueck[3]] = wert
            elif stueck[1] == "fahrzeuge" and len(stueck) == 4:
                kataloge["fahrzeuge"].setdefault(stueck[2], {"id": stueck[2]})[stueck[3]] = wert
            continue
        if stueck[0] != "alarme" or len(stueck) < 3:
            continue

        alarm = alarme.setdefault(stueck[1], _leerer_alarm(stueck[1]))
        rest = stueck[2:]
        if len(rest) == 1:
            alarm[rest[0]] = wert
        elif rest[0] in ("anfahrtsadresse", "einsatzadresse", "karte"):
            alarm[rest[0]][rest[1]] = wert
        elif rest[0] == "hinweise" and len(rest) == 3:
            alarm.setdefault("_hinweise", {}).setdefault(rest[1], {"id": rest[1]})[rest[2]] = wert
        elif rest[0] == "einsatzmittel" and len(rest) >= 3:
            gruppe = alarm.setdefault("_gruppen", {}).setdefault(
                rest[1], {"id": rest[1], "_fahrzeuge": {}})
            if rest[2] == "fahrzeuge" and len(rest) == 5:
                gruppe["_fahrzeuge"].setdefault(rest[3], {"id": rest[3]})[rest[4]] = wert
            elif len(rest) == 3:
                gruppe[rest[2]] = wert

    def geordnet(eintraege: dict) -> list:
        return sorted(eintraege.values(), key=lambda e: (e.get("sortierung", 0), e["id"]))

    fertig = []
    for alarm in geordnet(alarme):
        alarm["hinweise"] = geordnet(alarm.pop("_hinweise", {}))
        gruppen = []
        for gruppe in geordnet(alarm.pop("_gruppen", {})):
            gruppe["fahrzeuge"] = geordnet(gruppe.pop("_fahrzeuge", {}))
            gruppen.append(gruppe)
        alarm["einsatzmittel"] = gruppen
        fertig.append(alarm)

    # Sorted by what they read as, not by their ids, so both sides agree on the order.
    kataloge["fahrzeuge"] = sorted(kataloge["fahrzeuge"].values(),
                                   key=lambda v: (v.get("funkrufname", ""), v["id"]))
    kataloge["stichwoerter"] = sorted(kataloge["stichwoerter"].values(),
                                      key=lambda e: (e.get("text", ""), e["id"]))
    for liste in ("status", "trupp"):
        kataloge[liste].sort()

    for liste in PLANUNGSEINTRAEGE:
        planung[liste] = geordnet(planung[liste])
    for person in planung["personen"]:
        person["verfuegbar"] = geordnet(person.pop("_verfuegbar", {}))
    for lauf in planung["laeufe"]:
        schritte = geordnet(lauf.pop("_schritte", {}))
        for schritt in schritte:
            schritt["besatzung"] = geordnet(schritt.pop("_besatzung", {}))
        lauf["schritte"] = schritte
    for liste in PLANUNGSLISTEN:
        planung[liste].sort()

    return {"version": 1, "alarme": fertig, "kataloge": kataloge, "planung": planung}


class Dokument:
    """
    The merged state: every path with the value and the revision it was written at, plus the
    tombstones. `stand` counts up with every accepted write, and is what a client asks changes
    since.
    """

    def __init__(self, eintraege: dict[str, dict] | None = None, stand: int = 0):
        self.eintraege: dict[str, dict] = eintraege or {}
        self.stand = stand

    @classmethod
    def aus_arbeitsmappe(cls, arbeitsmappe: dict) -> "Dokument":
        dokument = cls()
        dokument.anwenden([{"pfad": pfad, "wert": wert}
                           for pfad, wert in flach(sortierung_setzen(arbeitsmappe)).items()],
                          "start")
        return dokument

    def _verdeckt(self, pfad: str) -> bool:
        """
        True when something this path hangs below has been deleted — the entity, not the field.

        Checked on the ancestors only, so a tombstone does not hide itself: it still has to reach
        the clients, or they would never learn about the deletion at all.
        """
        stueck = teile(pfad)
        for laenge in range(1, len(stueck)):
            eintrag = self.eintraege.get(_pfad(*stueck[:laenge]))
            if eintrag is not None and eintrag.get("weg"):
                return True
        return False

    def anwenden(self, aenderungen: list[dict], wer: str) -> int:
        """
        Writes a batch at one new revision. A change is taken unless what is already there was
        written later; a tie is settled by the writer's name, so every replica lands the same
        way. Returns the new revision.
        """
        if not aenderungen:
            return self.stand
        self.stand += 1
        for aenderung in aenderungen:
            pfad = aenderung["pfad"]
            # A field written into something already deleted is dropped rather than stored. The
            # writer had simply not heard about the deletion yet; keeping the value would mean
            # sending it on to everyone else, who would rebuild the deleted entity from it.
            if not aenderung.get("weg") and self._verdeckt(pfad):
                continue
            vorhanden = self.eintraege.get(pfad)
            if vorhanden and (vorhanden["stand"], vorhanden["wer"]) > (self.stand, wer):
                continue
            if aenderung.get("weg"):
                self.eintraege[pfad] = {"weg": True, "stand": self.stand, "wer": wer}
            else:
                self.eintraege[pfad] = {"wert": aenderung["wert"], "stand": self.stand,
                                        "wer": wer}
        return self.stand

    def seit(self, stand: int) -> list[dict]:
        return [{"pfad": pfad, **eintrag}
                for pfad, eintrag in self.eintraege.items()
                if eintrag["stand"] > stand and not self._verdeckt(pfad)]

    def arbeitsmappe(self) -> dict:
        lebend = {pfad: eintrag["wert"] for pfad, eintrag in self.eintraege.items()
                  if not eintrag.get("weg") and not self._verdeckt(pfad)}
        return rund(lebend)

    def sichern(self) -> dict:
        return {"stand": self.stand, "eintraege": self.eintraege}

    @classmethod
    def laden(cls, roh: dict) -> "Dokument":
        return cls(roh.get("eintraege", {}), roh.get("stand", 0))
