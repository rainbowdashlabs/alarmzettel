"""
Der Alarmzettel als PDF, gerendert aus der laufenden Sitzung.

Die Arbeitsmappe liegt ohnehin auf dem Server, also wird sie nicht noch einmal hochgeladen: der
Browser sagt nur, was er gedruckt haben will.

Der Sitzungsspeicher wird über das Modul angesprochen und nicht als Name hereingeholt, damit ein
Test ihn auf ein eigenes Verzeichnis umstellen kann, ohne das der laufenden Installation
anzurühren.
"""

import io
import zipfile

from fastapi import APIRouter, HTTPException, Request, Response

from data.ablaufplan import plandaten
from services.adressen import adressen
from data.alarmplan import ableitung, mit_plan
from data.geo import punkt_aus_text
from data.polar import polar_koordinaten
from data.katalog import mit_katalog
from data.typst import RenderError, plan_blattweise, render, render_plan
from entities.alarm import Arbeitsmappe
from data.sitzung import SitzungFehler
from services import sitzung as sitzungsdienst
from services.sitzung import COOKIE

router = APIRouter(prefix="/render", tags=["render"])


def _mappe(request: Request) -> Arbeitsmappe:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Keine laufende Sitzung.")
    try:
        echt, _ = sitzungsdienst.sitzungen.aufloesen(token)
        inhalt, _ = sitzungsdienst.sitzungen.lesen(echt)
    except SitzungFehler as fehler:
        raise HTTPException(status_code=404, detail=str(fehler)) from fehler
    return Arbeitsmappe.model_validate(inhalt)


def _blattbasis(request: Request) -> str:
    """
    Der Anfang der Lese-Links, mit denen jedes Blatt sein Kennmuster bekommt. Das Lesetoken
    entsteht dabei, falls es noch keines gibt — es ist dasselbe, das der Teilen-Knopf ausgibt.

    Ohne Sitzung bleibt die Basis leer und das Blatt ohne Kennmuster: ein Zettel darf nicht
    ungedruckt bleiben, weil ein Link fehlt.
    """
    token = request.cookies.get(COOKIE)
    if not token:
        return ""
    try:
        echt, _ = sitzungsdienst.sitzungen.aufloesen(token)
        nur_lesen = sitzungsdienst.sitzungen.lesetoken(echt)
    except SitzungFehler:
        return ""
    return str(request.base_url).rstrip("/") + f"/blatt/{nur_lesen}"


def _punkt_zu(adresse) -> dict | None:
    """
    Der Punkt einer Adresse: der an ihr gesetzte, sonst der des Adressdienstes. Ein gesetzter gilt
    vor der Straße — jemand hat ihn auf die Karte gesetzt, weil sie ihn nicht trifft.
    """
    gesetzt = punkt_aus_text(adresse.koordinaten)
    if gesetzt is not None:
        return gesetzt
    gefunden = adressen.finden(adresse.strasse, adresse.hnr, adresse.plz)
    if gefunden and gefunden.get("ostwert") is not None:
        return {"ostwert": gefunden["ostwert"], "nordwert": gefunden["nordwert"]}
    return None


def _mit_polar(mappe: Arbeitsmappe) -> Arbeitsmappe:
    """
    Die Polar-Koordinaten, wo keine stehen. Bisher entstanden sie nur, während jemand eine
    Adresse im Editor auflöste — ein Alarm, dessen Einsatzadresse aus dem Plan kommt oder der
    importiert wurde, ging ohne sie in den Druck. Ein eingetragener Wert bleibt stehen.
    """
    wache = _punkt_zu(mappe.kataloge.wache)
    if wache is None:
        return mappe
    alarme = []
    for alarm in mappe.alarme:
        ziel = None if alarm.karte.polarKoordinaten.strip() else _punkt_zu(alarm.einsatzadresse)
        if ziel is None:
            alarme.append(alarm)
            continue
        alarme.append(alarm.model_copy(update={"karte": alarm.karte.model_copy(
            update={"polarKoordinaten": polar_koordinaten(wache, ziel)})}))
    return mappe.model_copy(update={"alarme": alarme})


def _pdf(arbeitsmappe: Arbeitsmappe, filename: str) -> Response:
    try:
        pdf = render(_mit_polar(mit_katalog(mit_plan(arbeitsmappe, _ortspunkte(arbeitsmappe)))))
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


def _ortspunkte(mappe: Arbeitsmappe) -> dict:
    """
    Die Koordinaten der Orte, soweit sie bekannt sind. Sie tragen die geschätzten Fahrzeiten auf
    den Blättern; ohne Liste fehlt allein die Schätzung. Ein an der Adresse gesetzter Punkt gilt
    vor dem Adressdienst — jemand hat ihn auf die Karte gesetzt, weil die Straße ihn nicht trifft.
    """
    punkte = {}
    for ort in mappe.kataloge.alle_orte():
        punkt = _punkt_zu(ort.adresse)
        if punkt is not None:
            punkte[ort.id] = punkt
    return punkte


@router.post("/plan/ablauf")
def render_ablaufplan(request: Request) -> Response:
    """Der Ablaufplan: ein Blatt je Person, eines je Fahrzeug, und der Gesamtplan quer."""
    mappe = _mappe(request)
    try:
        pdf = render_plan(plandaten(mappe, _ortspunkte(mappe), _blattbasis(request)))
    except RenderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="ablaufplan.pdf"'})


@router.post("/plan/ablauf/zip")
def render_ablaufplan_zip(request: Request) -> Response:
    """
    Derselbe Plan als Archiv, ein PDF je Person und je Fahrzeug. Wer austeilt, greift damit den
    einen Zettel heraus, statt den ganzen Stapel zu blättern und zu trennen.
    """
    mappe = _mappe(request)
    daten = plandaten(mappe, _ortspunkte(mappe), _blattbasis(request))
    puffer = io.BytesIO()
    try:
        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as archiv:
            for name, teil in plan_blattweise(daten):
                archiv.writestr(name, render_plan(teil))
    except RenderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content=puffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="ablaufplan.zip"'})


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
    return {"abgeleitet": ableitung(mappe, alarm, _ortspunkte(mappe))}
