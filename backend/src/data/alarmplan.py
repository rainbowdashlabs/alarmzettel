"""
Der Alarmzettel aus dem Ablaufplan.

Zeigt eine Lage auf einen Alarm, dann weiß der Plan Dinge, die sonst von Hand einzutragen wären:
wann das Fahrzeug losfährt, wo die Lage stattfindet, wer mitfährt. Diese Felder kommen deshalb
beim Rendern aus dem Plan, und der Zettel entsteht je Fahrzeug einmal — er ist an genau eines
gerichtet, das ist der grau hinterlegte Funkrufname.

Ein Alarm, auf den keine Lage zeigt, verhält sich wie bisher; ohne eingeschaltete Planung ändert
sich überhaupt nichts.
"""

from data.kette import ankunft, fahrzeit, lagen_ort
from data.planzeit import minuten as _minuten
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


def _schritte_an(lauf: Lauf, punkt: Programmpunkt) -> list[tuple[int, Schritt]]:
    """
    Die Schritte dieser Kette, die auf diese Lage zeigen — auch die ohne Aufgebot, und auch eine
    Fahrt, die sie selbst trägt: dann ist ihr Beginn die Einsatzzeit.
    """
    return [(stelle, schritt) for stelle, schritt in enumerate(lauf.schritte)
            if schritt.programmpunktId == punkt.id]


def _lage_zu(arbeitsmappe: Arbeitsmappe, alarm: Alarm) -> Programmpunkt | None:
    if not arbeitsmappe.planung.aktiv:
        return None
    return next((punkt for punkt in arbeitsmappe.planung.programmpunkte
                 if punkt.alarmId == alarm.id), None)


def _beteiligte(arbeitsmappe: Arbeitsmappe, punkt: Programmpunkt,
                punkte: dict | None = None) -> list[dict]:
    """
    Die Fahrzeuge, die zu dieser Lage fahren, mit ihrer tatsächlichen Stärke und Zeit.

    Der EZP ist die geschätzte Fahrzeit dieses Fahrzeugs zur Lage — dieselbe Luftlinienrechnung
    wie im Ablaufplan. Ohne Koordinaten bleibt der Wert, den der Katalog führt.
    """
    koepfe = {person.id: person.anzahl for person in arbeitsmappe.kataloge.personen}
    namen = {person.id: person.name for person in arbeitsmappe.kataloge.personen}
    vorlagen = {fahrzeug.id: fahrzeug for fahrzeug in arbeitsmappe.kataloge.fahrzeuge}
    beteiligte = []
    for lauf in arbeitsmappe.planung.laeufe:
        for stelle, schritt in _schritte_an(lauf, punkt):
            vorlage = vorlagen.get(lauf.fahrzeugId)
            geschaetzt = fahrzeit(lauf, schritt, punkte or {})
            beteiligte.append({
                "vorlageId": lauf.fahrzeugId,
                "funkrufname": vorlage.funkrufname if vorlage else "",
                "staerke": str(sum(koepfe.get(platz.personId, 1) for platz in schritt.besatzung)),
                "beginn": _anfahrt(lauf, stelle),
                "ezp": "" if geschaetzt is None else str(geschaetzt),
                "von": schritt.von,
                "bis": schritt.bis,
                "da": ankunft(lauf, schritt, punkte or {}),
                "aufgebot": schritt.aufgebot and bool(lauf.fahrzeugId),
                "name": vorlage.funkrufname if vorlage else namen.get(lauf.personId, ""),
            })
    beteiligte.sort(key=lambda eintrag: eintrag["beginn"])
    return beteiligte


def _alarmierte(gruppe: list[dict]) -> list[dict]:
    """
    Wer aus dieser Gruppe auf den Zettel kommt: die alarmierten Fahrzeuge, jedes einmal. Wer nur
    Mimen bringt, steht am selben Ort und bleibt außen vor — er ist nicht alarmiert.
    """
    gesehen: dict[str, dict] = {}
    for eintrag in gruppe:
        if eintrag["aufgebot"] and eintrag["vorlageId"] not in gesehen:
            gesehen[eintrag["vorlageId"]] = eintrag
    return sorted(gesehen.values(), key=lambda eintrag: eintrag["beginn"])


def _gruppen(beteiligte: list[dict]) -> list[list[dict]]:
    """
    Ein Einsatz ist die Lage, einmal gelaufen: zusammen gehört, wessen Zeiten sich überschneiden.
    Ist zwischendurch niemand mehr da, ist der Einsatz zu Ende und der nächste fängt an — zwei
    Alarme nacheinander am selben Ort sind zwei Alarme, auch wenn sie auf dieselbe Lage zeigen.
    Die Überschneidung überträgt sich: A mit B und B mit C hält alle drei zusammen, auch wenn A
    und C einander nicht mehr berühren.

    Gruppiert wird über alle, die an der Lage stehen, und nicht nur über die Alarmierten: sonst
    fiele der Einsatz auseinander, sobald ihn ein Fahrzeug ohne Aufgebot überbrückt — und die
    Übersicht im Browser, die dieselbe Regel rechnet, zeigte etwas anderes als der Zettel.
    """
    gruppen: list[list[dict]] = []
    ende = None
    for eintrag in sorted(beteiligte, key=lambda kandidat: _minuten(kandidat["von"]) or 0):
        beginnt = _minuten(eintrag["von"]) or 0
        if ende is None or beginnt >= ende:
            gruppen.append([eintrag])
        else:
            gruppen[-1].append(eintrag)
        ende = max(ende or 0, _minuten(eintrag["bis"]) or 0)
    for gruppe in gruppen:
        gruppe.sort(key=lambda eintrag: eintrag["beginn"])
    return gruppen


def einsaetze(arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> list[dict]:
    """
    Alle Einsätze des Plans, nach Zeit sortiert: jede Lage so oft, wie sie läuft.

    Dieselbe Übersicht rechnet der Browser in `frontend/src/scripts/ablauf.ts`;
    `tools/plan_vergleichen` hält die beiden aneinander, denn davon hängt ab, wer zusammen auf
    einem Zettel steht.
    """
    gefunden = []
    for punkt in arbeitsmappe.planung.programmpunkte:
        for nummer, gruppe in enumerate(_gruppen(_beteiligte(arbeitsmappe, punkt, punkte)), 1):
            gefunden.append({
                "programmpunktId": punkt.id,
                "lage": punkt.name.strip() or _stichwort(arbeitsmappe, punkt),
                "nummer": nummer,
                "ortId": lagen_ort(arbeitsmappe.planung, punkt.id),
                "von": min(eintrag["beginn"] for eintrag in gruppe),
                "da": min(eintrag["da"] for eintrag in gruppe),
                "bis": max(eintrag["bis"] for eintrag in gruppe),
                "beteiligte": gruppe,
            })
    return sorted(gefunden, key=lambda einsatz: einsatz["von"])


def _stichwort(arbeitsmappe: Arbeitsmappe, punkt: Programmpunkt) -> str:
    alarm = next((eintrag for eintrag in arbeitsmappe.alarme if eintrag.id == punkt.alarmId), None)
    return alarm.stichwort.strip() if alarm else ""


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


def ableitung(arbeitsmappe: Arbeitsmappe, alarm: Alarm, punkte: dict | None = None) -> dict | None:
    """
    Was der Plan über diesen Alarm weiß, oder nichts, wenn keine Lage auf ihn zeigt. Der Editor
    zeigt genau das an, damit nichts gedruckt wird, was er nicht kennt.
    """
    punkt = _lage_zu(arbeitsmappe, alarm)
    if punkt is None:
        return None
    adresse = _adresse(arbeitsmappe, punkt)
    gruppen = [_alarmierte(gruppe)
               for gruppe in _gruppen(_beteiligte(arbeitsmappe, punkt, punkte))]
    gruppen = [gruppe for gruppe in gruppen if gruppe]
    return {
        "lage": punkt.name.strip() or alarm.stichwort,
        "einsatzadresse": adresse.model_dump() if adresse else None,
        "blaetter": [{
            "funkrufname": eintrag["funkrufname"],
            "staerke": eintrag["staerke"],
            "einsatzDatum": _datum(eintrag["beginn"]),
            "einsatzZeit": _uhrzeit(eintrag["beginn"]),
            "einsatzNr": _einsatznummer(gruppe, arbeitsmappe.kataloge.alarmeProTag),
            "ezp": eintrag["ezp"],
        } for gruppe in gruppen for eintrag in gruppe],
    }


def _blatt(alarm: Alarm, punkt: Programmpunkt, beteiligte: list[dict], fuer: dict,
           adresse, nummer: str = "") -> Alarm:
    """Ein Zettel, gerichtet an ein Fahrzeug. Das Aufgebot listet alle, die mit ihm alarmiert sind."""
    beginn = fuer["beginn"]
    gruppe = alarm.einsatzmittel[0].gruppe if alarm.einsatzmittel else ""
    fahrzeuge = [
        Fahrzeug(id=f"plan-{punkt.id}-{eintrag['vorlageId']}", sortierung=float(nummer),
                 vorlageId=eintrag["vorlageId"], funkrufname=eintrag["funkrufname"],
                 staerke=eintrag["staerke"], ezp=eintrag["ezp"],
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


def mit_plan(arbeitsmappe: Arbeitsmappe, punkte: dict | None = None) -> Arbeitsmappe:
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
        beteiligte = _beteiligte(arbeitsmappe, punkt, punkte)
        adresse = _adresse(arbeitsmappe, punkt)
        if not beteiligte:
            alarme.append(alarm.model_copy(
                update={"einsatzadresse": adresse} if adresse is not None else {}))
            continue
        gedruckt = False
        for gruppe in _gruppen(beteiligte):
            alarmierte = _alarmierte(gruppe)
            if not alarmierte:
                continue
            nummer = _einsatznummer(alarmierte, arbeitsmappe.kataloge.alarmeProTag)
            alarme += [_blatt(alarm, punkt, alarmierte, fuer, adresse, nummer)
                       for fuer in alarmierte]
            gedruckt = True
        if not gedruckt:
            alarme.append(alarm.model_copy(
                update={"einsatzadresse": adresse} if adresse is not None else {}))
    return arbeitsmappe.model_copy(update={"alarme": alarme})
