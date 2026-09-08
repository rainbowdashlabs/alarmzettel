"""
Address completion for the editor: street names, house numbers and one exact address.

The whole list would be pointless to send to a browser that needs a dozen rows of it, so the
queries run here. Every route answers normally when there is no downloaded list — an empty
result, not an error — because completion is a convenience and the fields work without it.
"""

from fastapi import APIRouter

from data.adressen import Adressen
from web.settings import settings

router = APIRouter(prefix="/adressen", tags=["adressen"])

adressen = Adressen(settings.adressen_datei, settings.adressen_tage)


@router.get("/status")
def status() -> dict:
    """What the editor asks once, to decide whether to offer completion at all."""
    return adressen.bestand()


@router.get("/suche")
def suche(q: str = "") -> list[dict]:
    """Streets while a name is being typed, doors once a house number follows it."""
    return adressen.suchen(q)


@router.get("")
def finden(strasse: str, hnr: str, plz: str = "") -> dict | None:
    return adressen.finden(strasse, hnr, plz)
