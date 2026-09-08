from fastapi import APIRouter

from services.adressen import router as adressen_router
from services.render import router as render_router
from services.sitzung import router as sitzung_router
from services.tabellenimport import router as import_router

router = APIRouter()

api = APIRouter(prefix="/api")
api.include_router(sitzung_router)
api.include_router(render_router)
api.include_router(import_router)
api.include_router(adressen_router)

router.include_router(api)
