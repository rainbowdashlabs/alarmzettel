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
        for feld in ("funkrufname", "staerke", "ezp", "status"):
            werte[_pfad(vbasis, feld)] = vorlage.get(feld, "")
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


def _leerer_alarm(kennung: str) -> dict:
    return {"id": kennung, "anfahrtsadresse": {}, "einsatzadresse": {}, "karte": {},
            "hinweise": [], "einsatzmittel": []}


def rund(werte: dict[str, Any]) -> dict:
    """Builds the working set back out of the flat map, in sort-key order."""
    alarme: dict[str, dict] = {}
    kataloge: dict[str, Any] = {"stichwoerter": {}, "status": [], "trupp": [], "fahrzeuge": {},
                                "arbeitsgruppe": "", "wache": {}}

    for pfad, wert in werte.items():
        stueck = teile(pfad)
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
    return {"version": 1, "alarme": fertig, "kataloge": kataloge}


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
