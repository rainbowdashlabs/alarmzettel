from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from data.freigabe import FreigabeFehler, Freigaben
from entities.alarm import Arbeitsmappe
from web.settings import settings

router = APIRouter(prefix="/freigabe", tags=["freigabe"])

freigaben = Freigaben(settings.freigabe_verzeichnis, settings.freigabe_tage)


class Aenderung(BaseModel):
    pfad: str
    wert: object | None = None
    weg: bool = False


class Stapel(BaseModel):
    """One client's edits plus the revision it last saw, so the answer can be the difference."""

    seit: int = 0
    wer: str = Field(min_length=1, max_length=64)
    aenderungen: list[Aenderung] = Field(default_factory=list, max_length=5000)


def _link(request: Request, token: str) -> str:
    return str(request.base_url).rstrip("/") + f"/freigabe/{token}"


def _oder_404(aufruf):
    try:
        return aufruf()
    except FreigabeFehler as fehler:
        raise HTTPException(status_code=404, detail=str(fehler)) from fehler


@router.post("")
def anlegen(arbeitsmappe: Arbeitsmappe, request: Request) -> dict:
    """
    Opens a shared workspace holding a copy of the working set. The token is the only thing
    protecting it, so the link is the secret: anyone who has it can read and edit until it
    expires.
    """
    if not arbeitsmappe.alarme:
        raise HTTPException(status_code=422, detail="Es gibt nichts zu teilen.")
    roh = arbeitsmappe.model_dump()
    if len(str(roh)) > settings.freigabe_max_bytes:
        raise HTTPException(status_code=413, detail="Die Arbeitsmappe ist zu groß zum Teilen.")

    token, laeuft_ab = freigaben.anlegen(roh)
    return {"token": token, "url": _link(request, token), "laeuftAb": laeuft_ab.isoformat(),
            "tage": settings.freigabe_tage}


@router.get("/{token}")
def lesen(token: str, request: Request) -> dict:
    inhalt, laeuft_ab = _oder_404(lambda: freigaben.lesen(token))
    return {"arbeitsmappe": inhalt, "laeuftAb": laeuft_ab.isoformat(),
            "url": _link(request, token), "tage": settings.freigabe_tage}


@router.get("/{token}/aenderungen")
def abholen(token: str, seit: int = 0) -> dict:
    """What has happened since `seit`. This is what the browser asks for every few seconds."""
    return _oder_404(lambda: freigaben.stand(token, seit))


@router.post("/{token}/aenderungen")
def einreichen(token: str, stapel: Stapel) -> dict:
    """
    Takes one client's edits and answers with everything it has not seen yet. Sending and
    receiving are the same round trip, so a client is never told about its own write twice.
    """
    return _oder_404(lambda: freigaben.schreiben(
        token, [a.model_dump() for a in stapel.aenderungen], stapel.wer, stapel.seit))


@router.delete("/{token}")
def loeschen(token: str) -> dict:
    return {"geloescht": freigaben.loeschen(token)}
