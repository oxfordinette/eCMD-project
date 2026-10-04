"""Référentiel des pathologies (administration) et documents types associés."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import storage
from ..db import get_db
from ..models import Pathologie, PathologieDocument
from ..schemas import GroupeOut, PathologieDocumentOut, PathologieIn, PathologieOut, PathologieResume
from .referentiels import PATHO_GROUPES

router = APIRouter(prefix="/api/pathologies", tags=["pathologies"])
CIBLE = "pathologie_document"


def _load(db: Session, code: str) -> Pathologie:
    p = db.scalar(select(Pathologie).options(selectinload(Pathologie.documents)).where(Pathologie.code == code))
    if not p:
        raise HTTPException(404, "Pathologie introuvable")
    return p


def _out(db: Session, p: Pathologie) -> PathologieOut:
    out = PathologieOut.model_validate(p)
    avec = storage.ids_avec_fichier(db, CIBLE, [d.id for d in p.documents])
    for d in out.documents:
        d.a_fichier = d.id in avec
    return out


@router.get("", response_model=list[PathologieResume])
def lister(
    db: Session = Depends(get_db),
    q: str | None = None,
    groupe: str | None = None,
    categorie: str | None = None,
):
    nb_docs = (
        select(func.count(PathologieDocument.id))
        .where(PathologieDocument.pathologie_code == Pathologie.code)
        .correlate(Pathologie)
        .scalar_subquery()
    )
    stmt = select(Pathologie, nb_docs)
    if groupe:
        stmt = stmt.where(Pathologie.groupe == groupe)
    if categorie:
        stmt = stmt.where(Pathologie.categorie == categorie)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Pathologie.code.ilike(like),
                Pathologie.libelle.ilike(like),
                Pathologie.synonymes.ilike(like),
                Pathologie.categorie.ilike(like),
            )
        )
    rows = db.execute(stmt.order_by(Pathologie.code)).all()
    out = []
    for p, n in rows:
        r = PathologieResume.model_validate(p)
        r.nb_documents = n or 0
        out.append(r)
    return out


@router.get("/groupes", response_model=list[GroupeOut])
def groupes(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Pathologie.groupe, func.count()).group_by(Pathologie.groupe)).all())
    noms = PATHO_GROUPES + sorted(g for g in counts if g not in PATHO_GROUPES)
    return [GroupeOut(groupe=g, nb=counts.get(g, 0)) for g in noms]


@router.get("/{code}", response_model=PathologieOut)
def detail(code: str, db: Session = Depends(get_db)):
    return _out(db, _load(db, code))


@router.post("", response_model=PathologieOut, status_code=201)
def creer(body: PathologieIn, db: Session = Depends(get_db)):
    code = body.code.strip().upper()
    if db.get(Pathologie, code):
        raise HTTPException(409, f"Le code {code} existe déjà")
    p = Pathologie(**body.model_dump(exclude={"code"}), code=code)
    db.add(p)
    db.commit()
    return _out(db, _load(db, code))


@router.put("/{code}", response_model=PathologieOut)
def modifier(code: str, body: PathologieIn, db: Session = Depends(get_db)):
    p = _load(db, code)
    for k, v in body.model_dump(exclude={"code"}).items():
        setattr(p, k, v)
    db.commit()
    return _out(db, _load(db, code))


@router.post("/{code}/documents", response_model=PathologieOut)
async def ajouter_document(
    code: str,
    fichier: UploadFile = File(...),
    nom: str | None = Form(None),
    db: Session = Depends(get_db),
):
    p = _load(db, code)
    data, mime = await storage.lire_upload(fichier)
    nom_fichier = fichier.filename or "document"
    doc = PathologieDocument(
        nom=(nom or "").strip() or nom_fichier,
        type=storage.type_document(nom_fichier),
        taille=storage.taille_lisible(len(data)),
    )
    p.documents.append(doc)
    db.flush()
    storage.enregistrer(db, CIBLE, doc.id, nom_fichier, mime, data)
    db.commit()
    return _out(db, _load(db, code))


@router.delete("/{code}/documents/{doc_id}", response_model=PathologieOut)
def supprimer_document(code: str, doc_id: int, db: Session = Depends(get_db)):
    p = _load(db, code)
    doc = next((d for d in p.documents if d.id == doc_id), None)
    if not doc:
        raise HTTPException(404, "Document introuvable")
    storage.supprimer(db, CIBLE, doc_id)
    p.documents.remove(doc)
    db.commit()
    return _out(db, _load(db, code))
