"""Stockage du contenu des fichiers : dans Lakebase (bytea) ou dans un Volume Unity Catalog."""
from __future__ import annotations

import io
import mimetypes
import uuid
from functools import lru_cache

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Fichier

EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}


@lru_cache
def _workspace():
    from databricks.sdk import WorkspaceClient

    return WorkspaceClient()


def type_document(nom_fichier: str) -> str:
    ext = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    if ext in {"jpg", "jpeg", "png"}:
        return "img"
    if ext == "pdf":
        return "pdf"
    return "other"


def taille_lisible(n: int) -> str:
    return f"{n / 1048576:.1f} Mo" if n > 1048576 else f"{max(1, round(n / 1024))} Ko"


async def lire_upload(upload: UploadFile) -> tuple[bytes, str]:
    s = get_settings()
    nom = upload.filename or "document"
    ext = "." + nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
    if ext not in EXTENSIONS:
        raise HTTPException(422, "Format non accepté (PDF, images, Word)")
    data = await upload.read()
    if len(data) > s.max_upload_mo * 1048576:
        raise HTTPException(413, f"Fichier trop volumineux (max {s.max_upload_mo} Mo)")
    mime = upload.content_type or mimetypes.guess_type(nom)[0] or "application/octet-stream"
    return data, mime


def enregistrer(db: Session, cible: str, cible_id: int, nom_fichier: str, mime: str, data: bytes) -> Fichier:
    s = get_settings()
    f = Fichier(cible=cible, cible_id=cible_id, nom_fichier=nom_fichier, mime=mime, taille_octets=len(data))
    if s.storage_mode == "volume":
        if not s.uc_volume_path:
            raise HTTPException(500, "STORAGE_MODE=volume mais UC_VOLUME_PATH est vide")
        chemin = f"{s.uc_volume_path.rstrip('/')}/{cible}/{cible_id}/{uuid.uuid4().hex}_{nom_fichier}"
        _workspace().files.upload(chemin, io.BytesIO(data), overwrite=True)
        f.chemin_volume = chemin
    else:
        f.contenu = data
    db.add(f)
    return f


def trouver(db: Session, cible: str, cible_id: int) -> Fichier | None:
    return db.scalar(select(Fichier).where(Fichier.cible == cible, Fichier.cible_id == cible_id))


def lire(f: Fichier) -> bytes:
    if f.chemin_volume:
        return _workspace().files.download(f.chemin_volume).contents.read()
    return f.contenu or b""


def supprimer(db: Session, cible: str, cible_id: int) -> None:
    f = trouver(db, cible, cible_id)
    if f and f.chemin_volume:
        try:
            _workspace().files.delete(f.chemin_volume)
        except Exception:  # noqa: BLE001  (le fichier a pu être supprimé à la main)
            pass
    db.execute(delete(Fichier).where(Fichier.cible == cible, Fichier.cible_id == cible_id))


def supprimer_fichier(db: Session, f: Fichier) -> None:
    if f.chemin_volume:
        try:
            _workspace().files.delete(f.chemin_volume)
        except Exception:  # noqa: BLE001
            pass
    db.delete(f)


def ids_avec_fichier(db: Session, cible: str, ids: list[int]) -> set[int]:
    if not ids:
        return set()
    return set(db.scalars(select(Fichier.cible_id).where(Fichier.cible == cible, Fichier.cible_id.in_(ids))))
