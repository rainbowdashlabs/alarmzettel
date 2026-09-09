from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, model_validator

from entities.basis import Adresse, Eintrag, kennung as _kennung
from entities.planung import DIENSTSTELLE, Ort, Person, Planung, Tag

__all__ = ["Adresse", "Eintrag", "Karte", "Fahrzeug", "Einsatzmittelgruppe", "HinweisText",
           "HinweisCode", "Hinweis", "Alarm", "Fahrzeugvorlage", "Stichwortvorlage", "Kataloge",
           "Arbeitsmappe", "Planung", "Ort", "Person", "Tag", "Materialvorlage",
           "DIENSTSTELLE"]


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
    """Wie viele Köpfe hineinpassen. Nur für den Ablaufplan; der Alarmzettel kennt das nicht."""
    plaetze: str = ""
    """Welche Fahrerlaubnisklasse es verlangt, gegen `Person.fahrerlaubnis` geprüft."""
    fuehrerschein: str = ""


class Materialvorlage(BaseModel):
    """
    Ein Stück Material, wie die Wache es führt. Ein Schritt zeigt darauf, damit ein Umbenennen
    jeden Plan erreicht, der es dabeihat.
    """

    id: str = Field(default_factory=_kennung)
    name: str = ""
    """
    Wie viel davon überhaupt da ist. Null heißt nicht erfasst — dann wird auch nicht gezählt,
    ob der Plan mehr verplant, als es gibt.
    """
    bestand: int = 0


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
    """
    Die angelegten Orte. Ein Ort gehört der Wache und nicht einem einzelnen Übungstag — deshalb
    steht er hier neben den Fahrzeugen und nicht im Plan.
    """
    orte: list[Ort] = []
    """Was die Wache an Material führt. Neu Geschriebenes kommt von selbst dazu."""
    material: list[Materialvorlage] = []
    """
    Die Tage der Veranstaltung, das Personal und die Wörter, aus denen sich seine Rollen und
    Fahrerlaubnisklassen zusammensetzen. Alles, was die Wache dauerhaft führt, steht hier —
    damit es an einem Ort steht und nicht an zweien.
    """
    tage: list[Tag] = []
    personen: list[Person] = []
    rollen: list[str] = []
    fahrerlaubnisse: list[str] = []
    """One fixed value for the whole working set; every new Alarm starts with it."""
    arbeitsgruppe: str = ""
    """The station the sheets are written for; the Polar-Koordinaten are measured from it."""
    wache: Adresse = Adresse()
    """Wie die Dienststelle im Plan heißt. Sie ist ein Ort, den es immer gibt."""
    wacheName: str = ""
    """
    Wie viele Alarme die Leitstelle an einem Tag zählt. Daraus wird die Einsatznummer einer
    geplanten Lage: der Anteil des Tages, der bis zur Einsatzzeit vergangen ist. Null heißt,
    dass keine abgeleitet wird und die getippte stehen bleibt.
    """
    alarmeProTag: int = 2200

    def alle_orte(self) -> list[Ort]:
        """
        Die Dienststelle zuerst, dann die angelegten. Sie ist kein Eintrag, den jemand anlegt,
        sondern einer, den es gibt, solange die Wache eine Adresse hat — und deshalb auch keiner,
        den man löschen kann.
        """
        dienststelle = Ort(id=DIENSTSTELLE, sortierung=-1,
                           name=self.wacheName or "Dienststelle", adresse=self.wache)
        return [dienststelle, *self.orte]


class Arbeitsmappe(BaseModel):
    """The whole working set, as it is downloaded, uploaded and held in the browser."""

    @model_validator(mode="before")
    @classmethod
    def _orte_in_den_katalog(cls, werte: Any) -> Any:
        """
        Orte standen einmal im Plan. Sie gehören der Wache und nicht dem einzelnen Übungstag,
        also ziehen sie einmalig in den Katalog um — die Schritte zeigen ohnehin nur auf ihre id.
        """
        if not isinstance(werte, dict):
            return werte
        plan = werte.get("planung")
        kataloge = werte.get("kataloge")
        if not isinstance(plan, dict) or not isinstance(kataloge, (dict, type(None))):
            return werte
        alte = plan.get("orte")
        kataloge = kataloge or {}
        if alte and not kataloge.get("orte"):
            werte = {**werte, "kataloge": {**kataloge, "orte": alte}}
        return werte

    version: int = 1
    alarme: list[Alarm] = []
    kataloge: Kataloge = Kataloge()
    """Der Ablaufplan. Abschaltbar; solange er aus ist, ändert er am Alarmzettel nichts."""
    planung: Planung = Planung()
