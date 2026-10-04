"""Téléchargement / affichage du contenu des documents."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_db

router = APIRouter(prefix="/api/fichiers", tags=["fichiers"])

CIBLES = {"document": "document", "pathologie-document": "pathologie_document"}


@router.get("/{cible}/{cible_id}")
def telecharger(cible: str, cible_id: int, telecharger: bool = Query(False), db: Session = Depends(get_db)):
    if cible not in CIBLES:
        raise HTTPException(404, "Type de fichier inconnu")
    f = storage.trouver(db, CIBLES[cible], cible_id)
    if not f:
        raise HTTPException(404, "Aucun fichier pour ce document")
    mode = "attachment" if telecharger else "inline"
    return Response(
        content=storage.lire(f),
        media_type=f.mime,
        headers={"Content-Disposition": f"{mode}; filename*=UTF-8''{quote(f.nom_fichier)}"},
    )
