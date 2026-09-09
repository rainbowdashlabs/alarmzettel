"""
Der Alarmzettel aus dem Ablaufplan.

Zeigt eine Lage auf einen Alarm, dann weiß der Plan Dinge, die sonst von Hand einzutragen wären:
wann das Fahrzeug losfährt, wo die Lage stattfindet, wer mitfährt. Diese Felder kommen deshalb
beim Rendern aus dem Plan, und der Zettel entsteht je Fahrzeug einmal — er ist an genau eines
gerichtet, das ist der grau hinterlegte Funkrufname.

Ein Alarm, auf den keine Lage zeigt, verhält sich wie bisher; ohne eingeschaltete Planung ändert
sich überhaupt nichts.
"""

from data.kette import lagen_ort
from entities.alarm import Alarm, Arbeitsmappe, Einsatzmittelgruppe, Fahrzeug
from entities.planung import Lauf, Programmpunkt, Schritt


def _datum(zeitpunkt: str) -> str:
    """ISO steht im Plan, der Zettel druckt deutsch."""
    if len(zeitpunkt) < 10:
        return ""
    jahr, monat, tag = zeitpunkt[:10].split("-")
    return f"{tag}.{monat}.{jahr}"


def _uhrzeit(zeitpunkt: str) -> str:
    return zeitpunkt[11:16] if len(zeitpunkt) >= 16 else ""


def _nummer(beginn: str, pro_tag: int) -> str:
    """
    Die Einsatznummer aus der Uhrzeit: der Anteil des Tages, der bis dahin vergangen ist, mal die
    Alarme, die die Leitstelle an einem Tag zählt. Damit steigen die Nummern über den Tag und
    haben Lücken — wie im Echtbetrieb, wo dazwischen die der ganzen Stadt liegen.
    """
    if not pro_tag or len(beginn) < 16:
        return ""
    try:
        stunde, minute = int(beginn[11:13]), int(beginn[14:16])
    except ValueError:
        return ""
    return str(round((stunde * 60 + minute) / (24 * 60) * pro_tag))


def _anfahrt(lauf: Lauf, stelle: int) -> str:
    """
    Wann das Fahrzeug für diese Lage losfährt. Bei einer eingetragenen Fahrt ist es deren Beginn;
    sonst der Beginn des Aufenthalts, denn der ist der Aufbruch — die Fahrt dorthin entsteht aus
    ihm und dauert bis zur Ankunft.
    """
    schritt = lauf.schritte[stelle]
    vorher = lauf.schritte[stelle - 1] if stelle > 0 else None
    if vorher is not None and vorher.art == "fahrt" and vorher.ortId == schritt.ortId:
        return vorher.von
    return schritt.von


def _erster_schritt(lauf: Lauf, punkt: Programmpunkt) -> tuple[int, Schritt] | None:
    """
    Der Schritt, mit dem dieses Fahrzeug an der Lage ankommt — sofern es überhaupt zu ihr
    gehört. Ein Fahrzeug, das nur Mimen hinfährt, steht am selben Ort und bleibt trotzdem außen
    vor: es ist nicht alarmiert.
    """
    for stelle, schritt in enumerate(lauf.schritte):
        if schritt.programmpunktId == punkt.id and schritt.aufgebot:
            return stelle, schritt
    return None


def _lage_zu(arbeitsmappe: Arbeitsmappe, alarm: Alarm) -> Programmpunkt | None:
    if not arbeitsmappe.planung.aktiv:
        return None
    return next((punkt for punkt in arbeitsmappe.planung.programmpunkte
                 if punkt.alarmId == alarm.id), None)


def _beteiligte(arbeitsmappe: Arbeitsmappe, punkt: Programmpunkt) -> list[dict]:
    """Die Fahrzeuge, die zu dieser Lage fahren, mit ihrer tatsächlichen Stärke und Zeit."""
    koepfe = {person.id: person.anzahl for person in arbeitsmappe.kataloge.personen}
    vorlagen = {fahrzeug.id: fahrzeug for fahrzeug in arbeitsmappe.kataloge.fahrzeuge}
    beteiligte = []
    for lauf in arbeitsmappe.planung.laeufe:
        if not lauf.fahrzeugId:
            continue
        treffer = _erster_schritt(lauf, punkt)
        if treffer is None:
            continue
        stelle, schritt = treffer
        vorlage = vorlagen.get(lauf.fahrzeugId)
        beteiligte.append({
            "vorlageId": lauf.fahrzeugId,
            "funkrufname": vorlage.funkrufname if vorlage else "",
            "staerke": str(sum(koepfe.get(platz.personId, 1) for platz in schritt.besatzung)),
            "beginn": _anfahrt(lauf, stelle),
        })
    beteiligte.sort(key=lambda eintrag: eintrag["beginn"])
    return beteiligte


def _einsatznummer(beteiligte: list[dict], pro_tag: int) -> str:
    """
    Ein Einsatz trägt eine Nummer, auch wenn drei Fahrzeuge dazu fahren: sie kommt von dem, der
    zuerst losfährt. `beteiligte` steht nach Zeit sortiert, also ist das der erste.
    """
    return _nummer(beteiligte[0]["beginn"], pro_tag) if beteiligte else ""


def _adresse(arbeitsmappe: Arbeitsmappe, punkt: Programmpunkt):
    """Die Lage findet dort statt, wo die Schritte stehen, die auf sie zeigen."""
    ort_id = lagen_ort(arbeitsmappe.planung, punkt.id)
    ort = next((ort for ort in arbeitsmappe.kataloge.alle_orte() if ort.id == ort_id), None)
    return ort.adresse if ort else None


def ableitung(arbeitsmappe: Arbeitsmappe, alarm: Alarm) -> dict | None:
    """
    Was der Plan über diesen Alarm weiß, oder nichts, wenn keine Lage auf ihn zeigt. Der Editor
    zeigt genau das an, damit nichts gedruckt wird, was er nicht kennt.
    """
    punkt = _lage_zu(arbeitsmappe, alarm)
    if punkt is None:
        return None
    adresse = _adresse(arbeitsmappe, punkt)
    beteiligte = _beteiligte(arbeitsmappe, punkt)
    nummer = _einsatznummer(beteiligte, arbeitsmappe.kataloge.alarmeProTag)
    return {
        "lage": alarm.stichwort or punkt.name,
        "einsatzadresse": adresse.model_dump() if adresse else None,
        "blaetter": [{
            "funkrufname": eintrag["funkrufname"],
            "staerke": eintrag["staerke"],
            "einsatzDatum": _datum(eintrag["beginn"]),
            "einsatzZeit": _uhrzeit(eintrag["beginn"]),
            "einsatzNr": nummer,
        } for eintrag in beteiligte],
    }


def _blatt(alarm: Alarm, punkt: Programmpunkt, beteiligte: list[dict], fuer: dict,
           adresse, nummer: str = "") -> Alarm:
    """Ein Zettel, gerichtet an ein Fahrzeug. Das Aufgebot listet trotzdem alle."""
    beginn = fuer["beginn"]
    gruppe = alarm.einsatzmittel[0].gruppe if alarm.einsatzmittel else ""
    fahrzeuge = [
        Fahrzeug(id=f"plan-{punkt.id}-{eintrag['vorlageId']}", sortierung=float(nummer),
                 vorlageId=eintrag["vorlageId"], funkrufname=eintrag["funkrufname"],
                 staerke=eintrag["staerke"],
                 alarmFuer=eintrag["vorlageId"] == fuer["vorlageId"])
        for nummer, eintrag in enumerate(beteiligte)
    ]
    aenderung: dict = {
        "einsatzmittel": [Einsatzmittelgruppe(id=f"plan-{punkt.id}", sortierung=0.0,
                                              gruppe=gruppe, fahrzeuge=fahrzeuge)],
    }
    if beginn:
        aenderung |= {"einsatzDatum": _datum(beginn), "einsatzZeit": _uhrzeit(beginn),
                      "meldungDatum": _datum(beginn), "meldungZeit": _uhrzeit(beginn)}
        if nummer:
            aenderung["einsatzNr"] = nummer
    if adresse is not None:
        aenderung["einsatzadresse"] = adresse
    return alarm.model_copy(update=aenderung)


def mit_plan(arbeitsmappe: Arbeitsmappe) -> Arbeitsmappe:
    """
    Die Arbeitsmappe, wie sie zu drucken ist: aus jedem Alarm, auf den eine Lage zeigt, wird ein
    Zettel je beteiligtem Fahrzeug.

    Hängt an der Lage noch kein Fahrzeug, bleibt der Zettel der getippte — bis auf die Adresse,
    die der Ort der Lage ohnehin weiß. Ein leeres Aufgebot zu drucken hieße, den Zettel an
    niemanden zu adressieren, und der Zwischenzustand „Lage angelegt, Ketten noch nicht“ ist
    beim Planen der Normalfall.
    """
    alarme: list[Alarm] = []
    for alarm in arbeitsmappe.alarme:
        punkt = _lage_zu(arbeitsmappe, alarm)
        if punkt is None:
            alarme.append(alarm)
            continue
        beteiligte = _beteiligte(arbeitsmappe, punkt)
        adresse = _adresse(arbeitsmappe, punkt)
        if not beteiligte:
            alarme.append(alarm.model_copy(
                update={"einsatzadresse": adresse} if adresse is not None else {}))
            continue
        nummer = _einsatznummer(beteiligte, arbeitsmappe.kataloge.alarmeProTag)
        alarme += [_blatt(alarm, punkt, beteiligte, fuer, adresse, nummer)
                   for fuer in beteiligte]
    return arbeitsmappe.model_copy(update={"alarme": alarme})
