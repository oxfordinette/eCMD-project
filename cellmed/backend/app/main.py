import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import SessionLocal, init_db
from .routers import (
    dossiers,
    fichiers,
    pathologies,
    portail,
    referentiels,
    statistiques,
    utilisateurs,
)

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title="CellMed API", version="0.1.0", description="eCMD — portail opérateurs CellMed et portail assuré Certificat médical")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dossiers.router)
app.include_router(referentiels.router)
app.include_router(pathologies.router)
app.include_router(utilisateurs.router)
app.include_router(statistiques.router)
app.include_router(fichiers.router)
app.include_router(portail.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    from .notifications import preparer_aws

    preparer_aws()
    if settings.seed_on_startup:
        from .seed import seed_if_empty

        with SessionLocal() as db:
            seed_if_empty(db)
    from .open_data import preparer_demo

    with SessionLocal() as db:
        preparer_demo(db)


@app.get("/api/health")
def health():
    return {"status": "ok"}
