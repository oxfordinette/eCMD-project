"""Gestion des utilisateurs (administration) et profil de l'utilisateur courant."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Utilisateur as UtilisateurDB
from ..schemas import PreferencesIn, ProfilIn, Utilisateur, UtilisateurIn, UtilisateurOut

router = APIRouter(prefix="/api", tags=["utilisateurs"])


def _email_libre(db: Session, email: str, sauf_id: int | None = None) -> None:
    stmt = select(UtilisateurDB.id).where(func.lower(UtilisateurDB.email) == email.lower())
    if sauf_id:
        stmt = stmt.where(UtilisateurDB.id != sauf_id)
    if db.scalar(stmt):
        raise HTTPException(409, "Un utilisateur utilise déjà cet email")


@router.get("/utilisateurs", response_model=list[UtilisateurOut])
def lister(db: Session = Depends(get_db), q: str | None = None, role: str | None = None):
    stmt = select(UtilisateurDB)
    if role:
        stmt = stmt.where(UtilisateurDB.role == role)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                UtilisateurDB.nom.ilike(like),
                UtilisateurDB.prenom.ilike(like),
                UtilisateurDB.nom_affiche.ilike(like),
                UtilisateurDB.email.ilike(like),
            )
        )
    return db.scalars(stmt.order_by(UtilisateurDB.nom, UtilisateurDB.prenom)).all()


@router.post("/utilisateurs", response_model=UtilisateurOut, status_code=201)
def creer(body: UtilisateurIn, db: Session = Depends(get_db)):
    _email_libre(db, body.email)
    u = UtilisateurDB(**body.model_dump())
    u.email = body.email.lower()
    db.add(u)
    db.commit()
    return u


@router.put("/utilisateurs/{user_id}", response_model=UtilisateurOut)
def modifier(user_id: int, body: UtilisateurIn, db: Session = Depends(get_db)):
    u = db.get(UtilisateurDB, user_id)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    _email_libre(db, body.email, user_id)
    for k, v in body.model_dump().items():
        setattr(u, k, v)
    u.email = body.email.lower()
    db.commit()
    return u


@router.delete("/utilisateurs/{user_id}", status_code=204)
def supprimer(user_id: int, db: Session = Depends(get_db), me: Utilisateur = Depends(current_user)):
    if me.id == user_id:
        raise HTTPException(409, "Vous ne pouvez pas supprimer votre propre compte")
    u = db.get(UtilisateurDB, user_id)
    if not u:
        raise HTTPException(404, "Utilisateur introuvable")
    db.delete(u)
    db.commit()


# ── Profil de l'utilisateur courant ───────────────────────────────────────


def _moi(db: Session, me: Utilisateur) -> UtilisateurDB:
    u = db.get(UtilisateurDB, me.id) if me.id else None
    if not u:
        raise HTTPException(404, "Compte introuvable")
    return u


@router.get("/profil", response_model=UtilisateurOut)
def profil(db: Session = Depends(get_db), me: Utilisateur = Depends(current_user)):
    return _moi(db, me)


@router.put("/profil", response_model=UtilisateurOut)
def modifier_profil(body: ProfilIn, db: Session = Depends(get_db), me: Utilisateur = Depends(current_user)):
    u = _moi(db, me)
    if body.email.lower() != u.email:
        # L'email identifie le compte tant que le SSO n'est pas en place : on ne le change pas ici.
        raise HTTPException(409, "L'email identifie votre compte : il sera modifiable avec le SSO")
    u.nom_affiche = body.nom_affiche.strip()
    u.telephone = body.telephone
    u.langue = body.langue
    u.fuseau = body.fuseau
    db.commit()
    return u


@router.patch("/profil/preferences", response_model=UtilisateurOut)
def preferences(body: PreferencesIn, db: Session = Depends(get_db), me: Utilisateur = Depends(current_user)):
    u = _moi(db, me)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(u, k, v)
    db.commit()
    return u
