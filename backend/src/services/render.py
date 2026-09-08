"""
Der Alarmzettel als PDF, gerendert aus der laufenden Sitzung.

Die Arbeitsmappe liegt ohnehin auf dem Server, also wird sie nicht noch einmal hochgeladen: der
Browser sagt nur, was er gedruckt haben will.
"""

from fastapi import APIRouter, HTTPException, Request, Response

from data.ablaufplan import plandaten
from data.alarmplan import ableitung, mit_plan
from data.katalog import mit_katalog
from data.typst import RenderError, render, render_plan
from entities.alarm import Arbeitsmappe
from services.sitzung import COOKIE, sitzungen
from data.sitzung import SitzungFehler

router = APIRouter(prefix="/render", tags=["render"])


def _mappe(request: Request) -> Arbeitsmappe:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Keine laufende Sitzung.")
    try:
        inhalt, _ = sitzungen.lesen(token)
    except SitzungFehler as fehler:
        raise HTTPException(status_code=404, detail=str(fehler)) from fehler
    return Arbeitsmappe.model_validate(inhalt)


def _pdf(arbeitsmappe: Arbeitsmappe, filename: str) -> Response:
    try:
        pdf = render(mit_katalog(mit_plan(arbeitsmappe)))
    except RenderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.post("")
def render_sitzung(request: Request) -> Response:
    """Alles, was die Sitzung gerade hält, ein Blatt je Alarm."""
    return _pdf(_mappe(request), "alarmzettel.pdf")


@router.post("/{alarm_id}")
def render_alarm(alarm_id: str, request: Request) -> Response:
    """Ein einzelner Alarm — das, was die Vorschau beim Bearbeiten anfragt."""
    mappe = _mappe(request)
    treffer = [alarm for alarm in mappe.alarme if alarm.id == alarm_id]
    if not treffer:
        raise HTTPException(status_code=404, detail="Alarm nicht in der Sitzung.")
    return _pdf(Arbeitsmappe(version=mappe.version, alarme=treffer, kataloge=mappe.kataloge,
                             planung=mappe.planung),
                f"alarmzettel-{alarm_id}.pdf")


@router.post("/plan/ablauf")
def render_ablaufplan(request: Request) -> Response:
    """Der Ablaufplan: ein Blatt je Person, eines je Fahrzeug, und der Gesamtplan quer."""
    mappe = _mappe(request)
    try:
        pdf = render_plan(plandaten(mappe))
    except RenderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="ablaufplan.pdf"'})


@router.get("/plan/alarm/{alarm_id}")
def alarm_ableitung(alarm_id: str, request: Request) -> dict:
    """
    Was der Ablaufplan zu diesem Alarm beisteuert. Der Editor zeigt es an, statt es noch einmal
    zu rechnen — gedruckt wird, was hier steht.
    """
    mappe = _mappe(request)
    alarm = next((eintrag for eintrag in mappe.alarme if eintrag.id == alarm_id), None)
    if alarm is None:
        raise HTTPException(status_code=404, detail="Alarm nicht in der Sitzung.")
    return {"abgeleitet": ableitung(mappe, alarm)}
