from fastapi import APIRouter, Header, HTTPException, Response

from data.typst import RenderError, render
from entities.alarm import Arbeitsmappe
from services.session import require

router = APIRouter(prefix="/render", tags=["render"])


def _pdf(arbeitsmappe: Arbeitsmappe, filename: str) -> Response:
    try:
        pdf = render(arbeitsmappe)
    except RenderError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.post("")
def render_session(x_session_id: str | None = Header(default=None)) -> Response:
    """Renders everything the session currently holds, one sheet per Alarm."""
    session = require(x_session_id)
    return _pdf(session.arbeitsmappe, "alarmzettel.pdf")


@router.post("/{alarm_id}")
def render_alarm(alarm_id: str, x_session_id: str | None = Header(default=None)) -> Response:
    """Renders a single Alarm — what the preview pane asks for while editing."""
    session = require(x_session_id)
    mappe = session.arbeitsmappe
    treffer = [alarm for alarm in mappe.alarme if alarm.id == alarm_id]
    if not treffer:
        raise HTTPException(status_code=404, detail="Alarm nicht in der Sitzung.")
    return _pdf(Arbeitsmappe(version=mappe.version, alarme=treffer, kataloge=mappe.kataloge),
                f"alarmzettel-{alarm_id}.pdf")
