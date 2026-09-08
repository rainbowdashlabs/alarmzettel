from fastapi import APIRouter

from services.freigabe import router as freigabe_router
from services.render import router as render_router
from services.tabellenimport import router as import_router
from services.session import router as session_router

router = APIRouter()

api = APIRouter(prefix="/api")
api.include_router(session_router)
api.include_router(render_router)
api.include_router(import_router)
api.include_router(freigabe_router)

router.include_router(api)
