from datetime import timedelta

from fastapi import APIRouter, Header, HTTPException

from data.store import Session, SessionStore
from entities.alarm import Arbeitsmappe
from web.settings import settings

router = APIRouter(prefix="/session", tags=["session"])

sessions = SessionStore(timedelta(minutes=settings.session_ttl_minutes))


def require(session_id: str | None) -> Session:
    if not session_id:
        raise HTTPException(status_code=401, detail="Keine Sitzung angegeben.")
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sitzung abgelaufen.")
    return session


def header(x_session_id: str | None = Header(default=None)) -> Session:
    return require(x_session_id)


@router.post("")
def create() -> dict:
    session = sessions.create()
    return {"id": session.id, "secondsLeft": session.seconds_left}


@router.get("")
def status(x_session_id: str | None = Header(default=None)) -> dict:
    session = require(x_session_id)
    return {"id": session.id, "secondsLeft": session.seconds_left,
            "alarme": len(session.arbeitsmappe.alarme)}


@router.put("/arbeitsmappe")
def replace(arbeitsmappe: Arbeitsmappe, x_session_id: str | None = Header(default=None)) -> dict:
    session = require(x_session_id)
    session.arbeitsmappe = arbeitsmappe
    return {"secondsLeft": session.seconds_left, "alarme": len(arbeitsmappe.alarme)}


@router.delete("")
def drop(x_session_id: str | None = Header(default=None)) -> dict:
    return {"dropped": sessions.drop(x_session_id or "")}
