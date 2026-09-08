import uuid
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


def _kennung() -> str:
    return str(uuid.uuid4())


class Eintrag(BaseModel):
    """
    Anything that sits in a list carries an id and a sort key.

    Two people editing one Alarm touch different entries far more often than the same one, so the
    merge works per entry rather than per list — which needs an identity that survives a reorder.
    The sort key is fractional: an entry moved between two others takes the value between theirs,
    so moving one thing never rewrites the rest.
    """

    id: str = Field(default_factory=_kennung)
    sortierung: float = 0


class Adresse(BaseModel):
    strasse: str = ""
    hnr: str = ""
    objekt: str = ""
    plz: str = ""
    ort: str = ""


class Karte(BaseModel):
    kab: str = ""
    fwPlan: str = ""
    ePlan: str = ""
    polarKoordinaten: str = ""


class Fahrzeug(Eintrag):
    funkrufname: str = ""
    ezp: str = ""
    status: str = ""
    staerke: str = ""
    trupp: str = ""
    hinweis: str = ""
    """The sheet is addressed to one vehicle, and that vehicle's Funkrufname is the only cell
    printed on grey. At most one vehicle per Alarm carries this."""
    alarmFuer: bool = False


class Einsatzmittelgruppe(Eintrag):
    """One block of the Einsatzmittelaufgebot: a group name and its vehicles. The HA line above
    it prints the Alarm's Einsatzadresse, so the group carries no address of its own."""

    gruppe: str = ""
    fahrzeuge: list[Fahrzeug] = []


class HinweisText(Eintrag):
    typ: Literal["text"] = "text"
    text: str = ""


class HinweisCode(Eintrag):
    """
    A dispatch code and the path taken to reach it. The answers print as the numbered sentences
    that follow the code on the sheet, which is what the interrogation dialog writes.
    """

    typ: Literal["code"] = "code"
    code: str = ""
    meldung: str = ""
    antworten: list[str] = []


Hinweis = Annotated[Union[HinweisText, HinweisCode], Field(discriminator="typ")]


class Alarm(BaseModel):
    id: str
    behoerde: str = "Berliner Feuerwehr"
    titel: str = "Alarm für"
    einsatzNr: str = ""
    einsatzDatum: str = ""
    einsatzZeit: str = ""
    meldungDatum: str = ""
    meldungZeit: str = ""
    aPlatz: str = ""
    polizei: str = ""
    sonderrechte: str = ""
    arbeitsgruppe: str = ""
    wachalarmNr: str = ""
    stichwort: str = ""
    kurzinfo: str = ""
    anfahrtsadresse: Adresse = Adresse()
    einsatzadresse: Adresse = Adresse()
    karte: Karte = Karte()
    meldungsquelle: str = ""
    rueckrufnummer: str = ""
    anrufer: str = ""
    betroffener: str = ""
    meldender: str = ""
    wasIstPassiert: str = ""
    hinweise: list[Hinweis] = []
    einsatzmittel: list[Einsatzmittelgruppe] = []


class Fahrzeugvorlage(BaseModel):
    """
    A vehicle as the station keeps it: crew strength, Einsatzpunkt and status are known in
    advance and come along when the vehicle is picked. Each stays editable on the Alarm.
    """

    funkrufname: str = ""
    staerke: str = ""
    ezp: str = ""
    status: str = ""


class Kataloge(BaseModel):
    """Suggestion lists the user maintains; the open data covers only the medical codes."""

    stichwoerter: list[str] = []
    fahrzeuge: list[Fahrzeugvorlage] = []
    status: list[str] = []
    trupp: list[str] = []
    """One fixed value for the whole working set; every new Alarm starts with it."""
    arbeitsgruppe: str = ""


class Arbeitsmappe(BaseModel):
    """The whole working set, as it is downloaded, uploaded and held in the browser."""

    version: int = 1
    alarme: list[Alarm] = []
    kataloge: Kataloge = Kataloge()
