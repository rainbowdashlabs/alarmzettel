"""
A vehicle on an Alarm names a Funkrufname; what that vehicle is comes from the catalogue.

Leaving EZP, Stärke, Status or Trupp empty on the Alarm means "whatever the catalogue says for
this Funkrufname", so correcting a vehicle once corrects every sheet that calls for it. A value
written on the Alarm overrides that one field and nothing else.

The resolution happens here rather than in the template, because the sheet should print the same
whatever asked for it, and because a rule worth having is worth a test.
"""

from data.staerke import trupp_text
from entities.alarm import Adresse, Alarm, Arbeitsmappe, Fahrzeug, Fahrzeugvorlage


def _schluessel(funkrufname: str) -> str:
    return funkrufname.strip().lower()


def vorlagen(arbeitsmappe: Arbeitsmappe) -> dict[str, Fahrzeugvorlage]:
    """
    Every catalogue vehicle under both keys it can be found by: its id, which is what an Alarm
    points at, and its Funkrufname, which is all a hand-typed or imported row has to go on.
    """
    gefunden: dict[str, Fahrzeugvorlage] = {}
    for vorlage in arbeitsmappe.kataloge.fahrzeuge:
        if vorlage.funkrufname.strip():
            gefunden.setdefault(_schluessel(vorlage.funkrufname), vorlage)
        if vorlage.id:
            gefunden[vorlage.id] = vorlage
    return gefunden


def _trupp_aus_staerke(staerke: str) -> str:
    ziffern = staerke.strip()
    if not ziffern.isdigit():
        return ""
    return trupp_text(int(ziffern))


def aufloesen(fahrzeug: Fahrzeug, vorlage: Fahrzeugvorlage | None) -> Fahrzeug:
    """
    One vehicle as it prints. The Trupp line follows the strength that came out of the same
    resolution, so a strength taken from the catalogue brings its Trupps along, and a vehicle
    that points at a catalogue entry prints that entry's Funkrufname however it was renamed.
    """
    ezp = fahrzeug.ezp or (vorlage.ezp if vorlage else "")
    status = fahrzeug.status or (vorlage.status if vorlage else "")
    staerke = fahrzeug.staerke or (vorlage.staerke if vorlage else "")
    trupp = fahrzeug.trupp or _trupp_aus_staerke(staerke)
    verwiesen = vorlage if vorlage and fahrzeug.vorlageId == vorlage.id else None
    funkrufname = verwiesen.funkrufname if verwiesen else fahrzeug.funkrufname
    return fahrzeug.model_copy(
        update={"funkrufname": funkrufname, "ezp": ezp, "status": status,
                "staerke": staerke, "trupp": trupp})


def _stichwort(alarm: Alarm, stichwoerter: dict[str, str]) -> str:
    """What the Alarm points at, or what it says itself where it points at nothing."""
    return stichwoerter.get(alarm.stichwortId, alarm.stichwort)


def _anfahrt(alarm: Alarm) -> Adresse:
    """
    Wohin gefahren wird, ist die Einsatzadresse — außer jemand hat ausdrücklich eine andere
    Anfahrtsadresse eingetragen. Zwei Felder, die fast immer dasselbe tragen, würden sonst
    zweimal getippt und einmal vergessen.
    """
    getippt = alarm.anfahrtsadresse
    return getippt if any(getippt.model_dump().values()) else alarm.einsatzadresse


def mit_katalog(arbeitsmappe: Arbeitsmappe) -> Arbeitsmappe:
    """The working set with everything resolved against the catalogue, ready to render."""
    bekannt = vorlagen(arbeitsmappe)
    stichwoerter = {eintrag.id: eintrag.text for eintrag in arbeitsmappe.kataloge.stichwoerter}
    alarme = []
    for alarm in arbeitsmappe.alarme:
        gruppen = []
        for gruppe in alarm.einsatzmittel:
            fahrzeuge = [
                aufloesen(fahrzeug,
                          bekannt.get(fahrzeug.vorlageId)
                          or bekannt.get(_schluessel(fahrzeug.funkrufname)))
                for fahrzeug in gruppe.fahrzeuge
            ]
            gruppen.append(gruppe.model_copy(update={"fahrzeuge": fahrzeuge}))
        alarme.append(alarm.model_copy(update={
            "stichwort": _stichwort(alarm, stichwoerter), "einsatzmittel": gruppen,
            "anfahrtsadresse": _anfahrt(alarm)}))
    return arbeitsmappe.model_copy(update={"alarme": alarme})
