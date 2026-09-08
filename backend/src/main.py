import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from services.freigabe import freigaben
from services.session import sessions
from web.app import router
from web.settings import settings


async def _sweep_expired():
    """
    Sessions also expire on access, and a share is checked when it is read; this clears out the
    ones nobody comes back to. Shares are reaped far less often than sessions - their retention
    is measured in days.
    """
    runden = 0
    while True:
        await asyncio.sleep(settings.session_sweep_seconds)
        sessions.sweep()
        runden += 1
        if runden % 60 == 0:
            await asyncio.to_thread(freigaben.aufraeumen)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # A restart is the one moment the whole share directory is worth walking: it is also where
    # files orphaned by an unclean shutdown get picked up.
    await asyncio.to_thread(freigaben.aufraeumen)
    task = asyncio.create_task(_sweep_expired())
    yield
    task.cancel()


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
    return {"status": "ok", "sessions": len(sessions), "freigaben": freigaben.anzahl()}


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
