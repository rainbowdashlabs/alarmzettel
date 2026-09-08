"""
A vehicle on an Alarm names a Funkrufname; what that vehicle is comes from the catalogue.

Leaving EZP, Stärke, Status or Trupp empty on the Alarm means "whatever the catalogue says for
this Funkrufname", so correcting a vehicle once corrects every sheet that calls for it. A value
written on the Alarm overrides that one field and nothing else.

The resolution happens here rather than in the template, because the sheet should print the same
whatever asked for it, and because a rule worth having is worth a test.
"""

from data.staerke import trupp_text
from entities.alarm import Arbeitsmappe, Fahrzeug, Fahrzeugvorlage


def _schluessel(funkrufname: str) -> str:
    return funkrufname.strip().lower()


def vorlagen(arbeitsmappe: Arbeitsmappe) -> dict[str, Fahrzeugvorlage]:
    return {_schluessel(vorlage.funkrufname): vorlage
            for vorlage in arbeitsmappe.kataloge.fahrzeuge if vorlage.funkrufname.strip()}


def _trupp_aus_staerke(staerke: str) -> str:
    ziffern = staerke.strip()
    if not ziffern.isdigit():
        return ""
    return trupp_text(int(ziffern))


def aufloesen(fahrzeug: Fahrzeug, vorlage: Fahrzeugvorlage | None) -> Fahrzeug:
    """
    One vehicle as it prints. The Trupp line follows the strength that came out of the same
    resolution, so a strength taken from the catalogue brings its Trupps along.
    """
    ezp = fahrzeug.ezp or (vorlage.ezp if vorlage else "")
    status = fahrzeug.status or (vorlage.status if vorlage else "")
    staerke = fahrzeug.staerke or (vorlage.staerke if vorlage else "")
    trupp = fahrzeug.trupp or _trupp_aus_staerke(staerke)
    return fahrzeug.model_copy(
        update={"ezp": ezp, "status": status, "staerke": staerke, "trupp": trupp})


def mit_katalog(arbeitsmappe: Arbeitsmappe) -> Arbeitsmappe:
    """The working set with every vehicle resolved against the catalogue, ready to render."""
    bekannt = vorlagen(arbeitsmappe)
    alarme = []
    for alarm in arbeitsmappe.alarme:
        gruppen = []
        for gruppe in alarm.einsatzmittel:
            fahrzeuge = [aufloesen(fahrzeug, bekannt.get(_schluessel(fahrzeug.funkrufname)))
                         for fahrzeug in gruppe.fahrzeuge]
            gruppen.append(gruppe.model_copy(update={"fahrzeuge": fahrzeuge}))
        alarme.append(alarm.model_copy(update={"einsatzmittel": gruppen}))
    return arbeitsmappe.model_copy(update={"alarme": alarme})
