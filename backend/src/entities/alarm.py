from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from entities.basis import Adresse, Eintrag, kennung as _kennung
from entities.planung import Planung

__all__ = ["Adresse", "Eintrag", "Karte", "Fahrzeug", "Einsatzmittelgruppe", "HinweisText",
           "HinweisCode", "Hinweis", "Alarm", "Fahrzeugvorlage", "Stichwortvorlage", "Kataloge",
           "Arbeitsmappe", "Planung"]


class Karte(BaseModel):
    kab: str = ""
    fwPlan: str = ""
    ePlan: str = ""
    polarKoordinaten: str = ""


class Fahrzeug(Eintrag):
    """The catalogue entry this stands for; empty where the Funkrufname was typed by hand."""
    vorlageId: str = ""
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
    """The catalogue entry this stands for; empty where the Stichwort was typed by hand."""
    stichwortId: str = ""
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

    An Alarm points at the id, so renaming the vehicle reaches every sheet that calls for it.
    """

    id: str = Field(default_factory=_kennung)
    funkrufname: str = ""
    staerke: str = ""
    ezp: str = ""
    status: str = ""


class Stichwortvorlage(BaseModel):
    """A Stichwort is only its text, so the id is the whole reason an Alarm can follow a rename."""

    id: str = Field(default_factory=_kennung)
    text: str = ""


class Kataloge(BaseModel):
    """Suggestion lists the user maintains; the open data covers only the medical codes."""

    stichwoerter: list[Stichwortvorlage] = []
    fahrzeuge: list[Fahrzeugvorlage] = []
    status: list[str] = []
    trupp: list[str] = []
    """One fixed value for the whole working set; every new Alarm starts with it."""
    arbeitsgruppe: str = ""
    """The station the sheets are written for; the Polar-Koordinaten are measured from it."""
    wache: Adresse = Adresse()


class Arbeitsmappe(BaseModel):
    """The whole working set, as it is downloaded, uploaded and held in the browser."""

    version: int = 1
    alarme: list[Alarm] = []
    kataloge: Kataloge = Kataloge()
    """Der Ablaufplan. Abschaltbar; solange er aus ist, ändert er am Alarmzettel nichts."""
    planung: Planung = Planung()
