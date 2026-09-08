"""
Was Alarmzettel und Ablaufplan gemeinsam haben.

Liegt für sich, weil sonst ein Ring entsteht: der Plan braucht Adresse und Eintrag, und die
Arbeitsmappe im Alarmteil braucht den Plan.
"""

import uuid

from pydantic import BaseModel, Field


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


class Adresse(BaseModel):
    strasse: str = ""
    hnr: str = ""
    objekt: str = ""
    plz: str = ""
    ort: str = ""
