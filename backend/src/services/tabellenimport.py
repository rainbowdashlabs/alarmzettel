"""
Turns a row of the old spreadsheet into an Alarm.

The spreadsheet is one row per Alarm with one vehicle and the Hinweise squashed into a single
cell. Both of those are unpacked here: the vehicle becomes a one-group Einsatzmittelaufgebot, and
the Hinweise text is parsed back into the list of notes and interrogation paths it came from.

Nothing is stored. The upload is converted and handed straight back, and the browser keeps it.
"""

import re
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from data.dokument import sortierung_setzen
from data.staerke import staerke_aus_text, trupp_text
from data.tabelle import TabellenFehler, zeilen
from entities.alarm import (
    Adresse, Alarm, Arbeitsmappe, Einsatzmittelgruppe, Fahrzeug, HinweisCode, HinweisText, Karte,
)

router = APIRouter(prefix="/import", tags=["import"])

MAX_BYTES = 8 * 1024 * 1024

CODE_ZEILE = re.compile(r"^Code:\s*(?P<code>[0-9]{1,2}\s*-\s*[A-Za-z]\s*-\s*[0-9A-Za-z]+)\s*:\s*(?P<rest>.*)$")
ANTWORT = re.compile(r"(?:^|\s)(\d{1,2})\.\s+")


def _code_kompakt(anzeige: str) -> str:
    """`67-B-3` is how the sheet prints it; `67B03` is how the dataset stores it."""
    teile = [teil.strip() for teil in anzeige.split("-")]
    if len(teile) != 3:
        return anzeige.replace("-", "").replace(" ", "")
    protokoll, buchstabe, stufe = teile
    ziffern = re.match(r"\d+", stufe)
    suffix = stufe[ziffern.end():] if ziffern else stufe
    nummer = f"{int(ziffern.group()):02d}" if ziffern else ""
    return f"{protokoll.zfill(2)}{buchstabe.upper()}{nummer}{suffix}"


def _hinweise(text: str) -> list:
    """
    Splits the merged Hinweise cell back into entries. A line beginning `Code: 67-B-3:` becomes a
    code entry whose numbered sentences are the interrogation path; everything else is a note.
    """
    if not text.strip():
        return []

    eintraege = []
    for roh in re.split(r"\n\s*-\s*|\n(?=-\s)|^-\s*", text.strip(), flags=re.MULTILINE):
        zeile = " ".join(roh.split())
        if not zeile:
            continue
        treffer = CODE_ZEILE.match(zeile)
        if not treffer:
            eintraege.append(HinweisText(text=zeile))
            continue

        rest = treffer.group("rest").strip()
        # The path is numbered 1., 2., 3. in order, so only the next expected number starts an
        # answer. Without that, an ordinal inside a sentence — "(Anrufer 4. Hand)" — splits it.
        stellen = []
        erwartet = 1
        for stelle in ANTWORT.finditer(rest):
            if int(stelle.group(1)) == erwartet:
                stellen.append(stelle)
                erwartet += 1
        meldung = rest[:stellen[0].start()].strip() if stellen else rest
        antworten = []
        for i, stelle in enumerate(stellen):
            ende = stellen[i + 1].start() if i + 1 < len(stellen) else len(rest)
            antwort = rest[stelle.end():ende].strip()
            if antwort:
                antworten.append(antwort)
        eintraege.append(HinweisCode(code=_code_kompakt(treffer.group("code")),
                                     meldung=meldung, antworten=antworten))
    return eintraege


def alarm_aus_zeile(zeile: dict[str, str]) -> Alarm:
    holen = lambda *namen: next((zeile[n] for n in namen if zeile.get(n)), "")

    adresse = Adresse(strasse=holen("Straße", "Strasse"), hnr=holen("H.Nr.", "HNr"),
                      objekt=holen("Objekt"), plz=holen("PLZ"), ort=holen("Ort"))
    datum, zeitpunkt = holen("Datum"), holen("Zeit")

    # The old sheet listed identification numbers behind the strength; only the strength is
    # wanted now, and the Trupp line is rebuilt from it.
    roher_trupp = holen("Trupp")
    staerke = staerke_aus_text(roher_trupp)
    fahrzeug = Fahrzeug(funkrufname=holen("Funkrufname"), ezp=holen("EZP"),
                        status=holen("Status"),
                        staerke=str(staerke) if staerke else "",
                        trupp=trupp_text(staerke) if staerke else roher_trupp,
                        hinweis=holen("FzHinweis"), alarmFuer=True)

    return Alarm(
        id=str(uuid.uuid4()),
        einsatzNr=holen("Einsatz Nr", "Einsatz_Nr", "EinsatzNr"),
        einsatzDatum=datum, einsatzZeit=zeitpunkt,
        meldungDatum=datum, meldungZeit=zeitpunkt,
        stichwort=holen("Stichwort"), kurzinfo=holen("Kurzinfo"),
        anfahrtsadresse=adresse, einsatzadresse=adresse.model_copy(),
        karte=Karte(kab=holen("KaB"), polarKoordinaten=holen("Polar-Koord", "Polar-Koordinaten")),
        meldungsquelle=holen("Meldungsquelle"), rueckrufnummer=holen("Rückrufnummer"),
        anrufer=holen("Anrufer"), betroffener=holen("Betroffener"), meldender=holen("Meldender"),
        wasIstPassiert=holen("Was ist passiert"),
        hinweise=_hinweise(holen("Hinweise")),
        einsatzmittel=[Einsatzmittelgruppe(gruppe="keine Gruppe", fahrzeuge=[fahrzeug])],
    )


@router.post("")
async def tabelle_uebernehmen(datei: UploadFile = File(...)) -> Arbeitsmappe:
    inhalt = await datei.read()
    if len(inhalt) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Die Datei ist zu groß.")
    try:
        reihen = zeilen(inhalt)
    except TabellenFehler as fehler:
        raise HTTPException(status_code=422, detail=str(fehler)) from fehler
    if not reihen:
        raise HTTPException(status_code=422, detail="Die Tabelle enthält keine Zeilen.")
    mappe = Arbeitsmappe(alarme=[alarm_aus_zeile(reihe) for reihe in reihen])
    return Arbeitsmappe.model_validate(sortierung_setzen(mappe.model_dump()))
