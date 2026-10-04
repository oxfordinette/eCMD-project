"""Utilisateur courant.

En attendant le SSO : le compte est identifié par l'en-tête X-Forwarded-Email (posé par un proxy
d'authentification) ou, à défaut, par DEFAULT_USER_EMAIL. Il est créé dans la table utilisateur
s'il n'existe pas encore.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Utilisateur as UtilisateurDB
from .schemas import Utilisateur

ROLE_LABELS = {"admin": "Admin", "manager": "Manager", "medecin": "Médecin conseil", "gestionnaire": "Gestionnaire"}


def initiales(nom: str) -> str:
    """'Dr. Martin' -> 'DM', 'Sophie Martin' -> 'SM'."""
    parts = re.sub(r"[^\w\s-]", "", nom).split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def nom_affiche(u: UtilisateurDB) -> str:
    return u.nom_affiche or f"{u.prenom} {u.nom}".strip()


def compte_courant(db: Session, email: str | None = None) -> UtilisateurDB:
    s = get_settings()
    email = (email or s.default_user_email).lower()
    u = db.scalar(select(UtilisateurDB).where(UtilisateurDB.email == email))
    if u is None:
        u = UtilisateurDB(
            nom=s.default_user_name,
            prenom="",
            nom_affiche=s.default_user_name,
            titre=s.default_user_role,
            email=email,
            role="gestionnaire",
        )
        db.add(u)
        db.commit()
    return u


def current_user(
    db: Session = Depends(get_db),
    x_forwarded_email: str | None = Header(default=None),
) -> Utilisateur:
    u = compte_courant(db, x_forwarded_email)
    nom = nom_affiche(u)
    return Utilisateur(
        id=u.id,
        nom=nom,
        role=u.titre or ROLE_LABELS.get(u.role, u.role),
        initiales=initiales(nom),
        email=u.email,
    )


def marquer_connexion(db: Session, user_id: int) -> None:
    u = db.get(UtilisateurDB, user_id)
    if u:
        u.derniere_connexion = datetime.now(timezone.utc)
        db.commit()
