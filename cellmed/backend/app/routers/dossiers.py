"""API des dossiers CMD : listes, détail, actions du workflow, commentaires."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import storage
from ..auth import current_user
from ..db import get_db
from ..models import STATUTS, Commentaire, DeclarationAssure, Document, Dossier, Evenement, MedecinConseil, PieceRequise
from ..schemas import (
    ActionIn,
    AnalyseIn,
    AvisIn,
    CommentaireIn,
    DossierDetail,
    DossierList,
    DossierResume,
    ExpertiseIn,
    PiecesIn,
    Utilisateur,
    ValiderIn,
)

router = APIRouter(prefix="/api/dossiers", tags=["dossiers"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load(db: Session, dossier_id: str) -> Dossier:
    d = db.scalar(
        select(Dossier)
        .options(
            selectinload(Dossier.documents),
            selectinload(Dossier.evenements),
            selectinload(Dossier.commentaires),
            selectinload(Dossier.pieces_requises),
        )
        .where(Dossier.id == dossier_id)
    )
    if not d:
        raise HTTPException(404, "Dossier introuvable")
    return d


def _detail(db: Session, d: Dossier) -> DossierDetail:
    out = DossierDetail.model_validate(d)
    avec = storage.ids_avec_fichier(db, "document", [doc.id for doc in d.documents])
    for doc in out.documents:
        doc.a_fichier = doc.id in avec
    decl = db.get(DeclarationAssure, d.id)
    out.declaration = decl.recapitulatif if decl else None
    return out


def _goto(d: Dossier, status: str) -> None:
    d.status = status
    if status not in (d.parcours or []):
        d.parcours = [*(d.parcours or []), status]


def _event(d: Dossier, action: str, auteur: str, categorie: str) -> None:
    d.evenements.append(Evenement(date=_now(), action=action, auteur=auteur, categorie=categorie))


@router.get("/compteurs", response_model=dict[str, int])
def compteurs(db: Session = Depends(get_db)):
    rows = db.execute(select(Dossier.status, func.count()).group_by(Dossier.status)).all()
    out = {s: 0 for s in STATUTS}
    out.update({s: n for s, n in rows})
    return out


@router.get("", response_model=DossierList)
def lister(
    db: Session = Depends(get_db),
    status: str | None = None,
    q: str | None = None,
    urgence: str | None = None,
    type: str | None = None,
    pieces_statut: str | None = None,
    # Recherche avancée
    id: str | None = None,
    nom: str | None = None,
    prenom: str | None = None,
    nss: str | None = None,
    societe: str | None = None,
    sinistre: str | None = None,
    patho: str | None = None,
    debut_min: date | None = None,
    fin_max: date | None = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
    tri: str = Query("soumission", pattern="^(soumission|recent)$"),
):
    stmt = select(Dossier)
    if status:
        stmt = stmt.where(Dossier.status == status)
    if urgence:
        stmt = stmt.where(Dossier.urgence == urgence)
    if type:
        stmt = stmt.where(Dossier.type == type)
    if pieces_statut:
        stmt = stmt.where(Dossier.pieces_statut == pieces_statut)
    for col, val in (
        (Dossier.id, id),
        (Dossier.nom, nom),
        (Dossier.prenom, prenom),
        (Dossier.nss, nss),
        (Dossier.societe, societe),
        (Dossier.dossier_sinistre, sinistre),
    ):
        if val and val.strip():
            stmt = stmt.where(col.ilike(f"%{val.strip()}%"))
    if patho and patho.strip():
        like = f"%{patho.strip()}%"
        stmt = stmt.where(or_(Dossier.patho.ilike(like), Dossier.cim10.ilike(like)))
    if debut_min:
        stmt = stmt.where(Dossier.date_debut >= debut_min)
    if fin_max:
        stmt = stmt.where(Dossier.date_fin <= fin_max)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Dossier.id.ilike(like),
                Dossier.nom.ilike(like),
                Dossier.prenom.ilike(like),
                Dossier.patho.ilike(like),
                Dossier.cim10.ilike(like),
                Dossier.societe.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = Dossier.updated_at.desc() if tri == "recent" else Dossier.date_soumission.desc()
    items = db.scalars(stmt.order_by(order, Dossier.id.desc()).limit(limit).offset(offset)).all()
    return DossierList(total=total, items=[DossierResume.model_validate(d) for d in items])


@router.get("/{dossier_id}", response_model=DossierDetail)
def detail(dossier_id: str, db: Session = Depends(get_db)):
    return _detail(db, _load(db, dossier_id))


@router.post("/{dossier_id}/documents", response_model=DossierDetail)
async def ajouter_document(
    dossier_id: str,
    fichier: UploadFile = File(...),
    nom: str | None = Form(None),
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(current_user),
):
    d = _load(db, dossier_id)
    data, mime = await storage.lire_upload(fichier)
    nom_fichier = fichier.filename or "document"
    libelle = (nom or "").strip() or nom_fichier
    doc = Document(
        nom=libelle,
        type=storage.type_document(nom_fichier),
        taille=storage.taille_lisible(len(data)),
        position=len(d.documents),
    )
    d.documents.append(doc)
    db.flush()
    storage.enregistrer(db, "document", doc.id, nom_fichier, mime, data)
    _event(d, f"Document ajouté par le gestionnaire : {libelle}", user.nom, "systeme")
    db.commit()
    return _detail(db, _load(db, dossier_id))


@router.put("/{dossier_id}/analyse", response_model=DossierDetail)
def enregistrer_analyse(
    dossier_id: str,
    body: AnalyseIn,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(current_user),
):
    d = _load(db, dossier_id)
    d.analyse_compte_rendu = body.compte_rendu
    d.analyse_duree_estimee = body.duree_estimee
    _event(d, "Analyse du gestionnaire mise à jour", user.nom, "systeme")
    db.commit()
    return _detail(db, _load(db, dossier_id))


@router.post("/{dossier_id}/commentaires", response_model=DossierDetail)
def ajouter_commentaire(
    dossier_id: str,
    body: CommentaireIn,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(current_user),
):
    d = _load(db, dossier_id)
    d.commentaires.append(Commentaire(date=_now(), auteur=user.nom, role="Gestionnaire", texte=body.texte.strip()))
    db.commit()
    return _detail(db, _load(db, dossier_id))


@router.post("/{dossier_id}/pieces/{piece_id}/relance", response_model=DossierDetail)
def relancer_piece(
    dossier_id: str,
    piece_id: int,
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(current_user),
):
    d = _load(db, dossier_id)
    piece = next((p for p in d.pieces_requises if p.id == piece_id), None)
    if not piece:
        raise HTTPException(404, "Pièce introuvable")
    piece.nb_relances += 1
    _event(d, f"Relance envoyée à l'assuré pour la pièce manquante : {piece.nom}", user.nom, "pieces")
    db.commit()
    return _detail(db, _load(db, dossier_id))


@router.post("/{dossier_id}/actions", response_model=DossierDetail)
def action(
    dossier_id: str,
    body: Annotated[ActionIn, Body(discriminator="type")],
    db: Session = Depends(get_db),
    user: Utilisateur = Depends(current_user),
):
    d = _load(db, dossier_id)
    if d.status == "clotures":
        raise HTTPException(409, "Le dossier est clôturé")

    if isinstance(body, ValiderIn):
        d.decision = body.decision
        d.duree_validee = body.duree_validee
        _event(d, f"Dossier validé — {body.decision}", user.nom, "clotures")
        if body.commentaire:
            d.commentaires.append(
                Commentaire(date=_now(), auteur=user.nom, role="Gestionnaire", texte=body.commentaire.strip())
            )
        _goto(d, "clotures")
        _event(d, "Clôture du dossier", user.nom, "clotures")

    elif isinstance(body, PiecesIn):
        limite = date.today() + timedelta(days=body.delai_jours)
        d.pieces_requises.clear()
        for nom in body.pieces:
            d.pieces_requises.append(PieceRequise(nom=nom, statut="attente", date_limite=limite))
        d.pieces_statut = "attente"
        _goto(d, "pieces")
        _event(
            d,
            "Demande de pièces complémentaires envoyée à l'assuré — Documents demandés : " + ", ".join(body.pieces),
            user.nom,
            "pieces",
        )
        if body.message:
            d.commentaires.append(
                Commentaire(date=_now(), auteur=user.nom, role="Gestionnaire", texte=f"Message à l'assuré : {body.message.strip()}")
            )

    elif isinstance(body, (ExpertiseIn, AvisIn)):
        med = db.get(MedecinConseil, body.medecin_id)
        if not med:
            raise HTTPException(422, "Médecin conseil inconnu")
        label = f"{med.nom} — {med.specialite}"
        if isinstance(body, ExpertiseIn):
            _goto(d, "expertise")
            _event(d, f"Demande d'expertise médicale ({body.type_expertise}) — {label}", user.nom, "expertise")
        else:
            _goto(d, "avis-medical")
            delai = f" — délai {body.delai}" if body.delai else ""
            _event(d, f"Demande d'avis médical — {label}{delai}", user.nom, "avis-medical")
        if body.motif:
            d.commentaires.append(
                Commentaire(date=_now(), auteur=user.nom, role="Gestionnaire", texte=f"Motif : {body.motif.strip()}")
            )

    db.commit()
    return _detail(db, _load(db, dossier_id))
