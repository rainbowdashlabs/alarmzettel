"""
Was Alarmzettel und Ablaufplan gemeinsam haben.

Liegt für sich, weil sonst ein Ring entsteht: der Plan braucht Adresse und Eintrag, und die
Arbeitsmappe im Alarmteil braucht den Plan.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator


def kennung() -> str:
    return str(uuid.uuid4())


class Eintrag(BaseModel):
    """
    Anything that sits in a list carries an id and a sort key.

    Two people editing one Alarm touch different entries far more often than the same one, so the
    merge works per entry rather than per list — which needs an identity that survives a reorder.
    The sort key is fractional: an entry moved between two others takes the value between theirs,
    so moving one thing never rewrites the rest.
    """

    id: str = Field(default_factory=kennung)
    sortierung: float = 0

    @model_validator(mode="before")
    @classmethod
    def _leere_werte(cls, werte: Any) -> Any:
        """
        Ein leerer String, wo eine Zahl oder ein Ja oder Nein stehen sollte, ist kein Wert,
        sondern ein Feld, das es zu der Zeit noch nicht gab: der Flattener schrieb für alles
        Unbekannte "". Solche Felder bekommen ihre Vorgabe, statt eine Arbeitsmappe unlesbar zu
        machen, die vor der Erweiterung angelegt wurde.
        """
        if not isinstance(werte, dict):
            return werte
        leer = [name for name, feld in cls.model_fields.items()
                if feld.annotation in (bool, int, float) and werte.get(name) == ""]
        return {name: wert for name, wert in werte.items() if name not in leer} if leer else werte


class Adresse(BaseModel):
    strasse: str = ""
    hnr: str = ""
    objekt: str = ""
    plz: str = ""
    ort: str = ""
