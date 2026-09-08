import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from services.adressen import adressen
from services.sitzung import sitzungen
from web.app import router
from web.settings import settings


async def _aufraeumen():
    """
    Sitzungen laufen 30 Tage nach der letzten Benutzung ab. Das prüft niemand beim Zugriff, also
    geht hier in großem Abstand ein Aufräumer durch — die Frist ist in Tagen gemessen.
    """
    while True:
        await asyncio.sleep(settings.sitzung_sweep_seconds)
        await asyncio.to_thread(sitzungen.aufraeumen)


async def _adressen_holen():
    """
    Fetches the address list when there is none or the copy has aged out.

    Runs beside the server rather than before it: the download is a hundred megabytes and the
    application has to come up whether it succeeds, fails or never finishes. Until it lands,
    completion simply has nothing to offer.
    """
    if not settings.adressen_laden or not adressen.veraltet():
        return
    try:
        anzahl = await asyncio.to_thread(adressen.laden)
        logging.getLogger(__name__).info("Adressliste geladen: %s Einträge", anzahl)
    except Exception as fehler:
        logging.getLogger(__name__).warning("Adressliste nicht geladen: %s", fehler)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ein Neustart ist der eine Moment, in dem sich das ganze Verzeichnis zu durchlaufen lohnt:
    # hier werden auch die Dateien eingesammelt, die ein unsauberes Ende hinterlassen hat.
    await asyncio.to_thread(sitzungen.aufraeumen)
    aufgaben = [asyncio.create_task(_aufraeumen()), asyncio.create_task(_adressen_holen())]
    yield
    for aufgabe in aufgaben:
        aufgabe.cancel()


app = FastAPI(title="Alarmzettel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials="*" not in settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "sitzungen": sitzungen.anzahl(),
            "imSpeicher": sitzungen.im_speicher(),
            "adressen": adressen.bestand()["anzahl"]}


_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa(path: str):
        """Everything that is not an API route is the single page app."""
        candidate = _static / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static / "index.html")
