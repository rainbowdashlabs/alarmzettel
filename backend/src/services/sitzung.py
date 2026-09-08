"""
Sitzungen: anlegen, lesen, abgleichen, wechseln.

Das Token steht in einem Cookie, damit ein Reload oder ein Browserneustart nichts kostet, und im
Link, damit Teilen nichts anderes ist als den Link weiterzugeben. Beides ist derselbe Schlüssel —
eine Anmeldung gibt es nicht.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from data.sitzung import SitzungFehler, Sitzungen
from entities.alarm import Arbeitsmappe
from web.settings import settings

router = APIRouter(prefix="/sitzung", tags=["sitzung"])

sitzungen = Sitzungen(settings.sitzung_verzeichnis, settings.sitzung_tage,
                      settings.sitzung_cache_eintraege, settings.sitzung_cache_minuten)

COOKIE = "alarmzettel_sitzung"


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
    return str(request.base_url).rstrip("/") + f"/sitzung/{token}"


def _oder_404(aufruf):
    try:
        return aufruf()
    except SitzungFehler as fehler:
        raise HTTPException(status_code=404, detail=str(fehler)) from fehler


def _setzen(antwort: Response, request: Request, token: str) -> None:
    """
    Das Cookie hält so lange wie die Sitzung selbst und wird bei jedem Zugriff erneuert, damit
    Weiterarbeiten es am Leben hält. `Secure` nur hinter TLS, sonst kommt es lokal nie an.
    """
    antwort.set_cookie(
        COOKIE, token,
        max_age=settings.sitzung_tage * 24 * 60 * 60,
        httponly=False, samesite="lax", secure=request.url.scheme == "https", path="/")


def _kopf(request: Request, token: str, laeuft_ab) -> dict:
    return {"token": token, "url": _link(request, token),
            "laeuftAb": laeuft_ab.isoformat(), "tage": settings.sitzung_tage}


@router.post("")
def anlegen(arbeitsmappe: Arbeitsmappe, request: Request, antwort: Response) -> dict:
    """
    Legt eine Sitzung mit dieser Arbeitsmappe an und macht sie zur laufenden. Eine leere
    Arbeitsmappe ist erlaubt — eine neue Sitzung fängt bei nichts an.
    """
    roh = arbeitsmappe.model_dump()
    if len(str(roh)) > settings.sitzung_max_bytes:
        raise HTTPException(status_code=413, detail="Die Arbeitsmappe ist zu groß.")

    token, laeuft_ab = sitzungen.anlegen(roh)
    _setzen(antwort, request, token)
    return _kopf(request, token, laeuft_ab)


@router.get("")
def laufende(request: Request, antwort: Response) -> dict:
    """Die Sitzung aus dem Cookie, samt Inhalt. 404, solange dieser Browser keine hat."""
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=404, detail="Keine laufende Sitzung.")
    inhalt, laeuft_ab = _oder_404(lambda: sitzungen.lesen(token))
    _setzen(antwort, request, token)
    return {"arbeitsmappe": inhalt, **_kopf(request, token, laeuft_ab)}


@router.get("/{token}")
def lesen(token: str, request: Request) -> dict:
    """Eine Sitzung ansehen, ohne in sie zu wechseln — das tut erst `uebernehmen`."""
    inhalt, laeuft_ab = _oder_404(lambda: sitzungen.lesen(token))
    return {"arbeitsmappe": inhalt, **_kopf(request, token, laeuft_ab)}


@router.post("/{token}/uebernehmen")
def uebernehmen(token: str, request: Request, antwort: Response) -> dict:
    """Diese Sitzung wird die laufende. Das ist der Sitzungswechsel und das Beitreten in einem."""
    _, laeuft_ab = _oder_404(lambda: sitzungen.lesen(token))
    _setzen(antwort, request, token)
    return _kopf(request, token, laeuft_ab)


@router.get("/{token}/aenderungen")
def abholen(token: str, seit: int = 0) -> dict:
    """What has happened since `seit`. This is what the browser asks for every few seconds."""
    return _oder_404(lambda: sitzungen.stand(token, seit))


@router.post("/{token}/aenderungen")
def einreichen(token: str, stapel: Stapel) -> dict:
    """
    Takes one client's edits and answers with everything it has not seen yet. Sending and
    receiving are the same round trip, so a client is never told about its own write twice.
    """
    return _oder_404(lambda: sitzungen.schreiben(
        token, [a.model_dump() for a in stapel.aenderungen], stapel.wer, stapel.seit))


@router.delete("/{token}")
def loeschen(token: str) -> dict:
    return {"geloescht": sitzungen.loeschen(token)}
