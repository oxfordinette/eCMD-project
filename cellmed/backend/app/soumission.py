"""Création du dossier CellMed à partir d'une déclaration soumise sur le portail Certificat médical.

Code partagé :
  - par le backend (SOUMISSION_MODE=direct : création immédiate, mode de développement) ;
  - par la Lambda « ecmd-creer-dossier » de la machine à états « ecmd-soumission-certificat »
    (SOUMISSION_MODE=step_functions), qui l'embarque tel quel (voir integration/step-functions).

Ne dépend ni de FastAPI ni du stockage des fichiers : uniquement des modèles et des règles du formulaire.
La fonction est idempotente : si l'invitation a déjà un dossier, il est renvoyé tel quel.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import portail_logic as pl
from .config import get_settings
from .models import Commentaire, DeclarationAssure, Document, Dossier, Evenement, Fichier, Invitation, Pathologie

log = logging.getLogger("cellmed.soumission")
CIBLE_PIECE = "invitation"


class SoumissionInvalide(Exception):
    """L'invitation ne peut pas (ou plus) donner lieu à un dossier : pas de réessai."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def nouvel_id(db: Session) -> str:
    annee = date.today().year
    prefixe = f"MQC-{annee}-"
    ids = db.scalars(select(Dossier.id).where(Dossier.id.like(f"{prefixe}%"))).all()
    nums = [int(m.group(1)) for i in ids if (m := re.match(rf"{prefixe}(\d+)$", i))]
    return f"{prefixe}{(max(nums) + 1 if nums else 1):05d}"


def libelles_pathologies(db: Session) -> dict[str, str]:
    return {p.code: p.libelle for p in db.scalars(select(Pathologie))}


def admin_invitation(inv: Invitation) -> dict:
    return {
        "entreprise": inv.entreprise,
        "numero_contrat": inv.numero_contrat,
        "assureur": inv.assureur,
        "nom": inv.nom,
        "prenom": inv.prenom,
        "date_naissance": inv.date_naissance.isoformat(),
        "nss": inv.nss,
        "nss_formate": pl.format_nss(inv.nss),
        "type_certificat": inv.type_certificat,
    }


def creer_dossier(db: Session, inv: Invitation) -> Dossier:
    """Crée le dossier CellMed (statut « À valider »), ses documents, son historique et la déclaration.

    Ne valide pas le formulaire (fait au moment de la soumission) ; ne fait pas de commit.
    """
    if inv.dossier_id:
        d = db.get(Dossier, inv.dossier_id)
        if d:
            return d
    if inv.statut != "soumise":
        raise SoumissionInvalide(f"Invitation {inv.id} au statut « {inv.statut} » : déclaration non soumise")

    b = dict(inv.brouillon or {})
    b.setdefault("documents", [])
    a = b.get("arret") or {}
    patho = db.get(Pathologie, a.get("pathologie_code")) if a.get("pathologie_code") else None
    now = _now()
    d = Dossier(
        id=nouvel_id(db),
        status="valider",
        parcours=["valider"],
        type=inv.type_certificat,
        type_cert=inv.type_certificat,
        nom=inv.nom.upper(),
        prenom=inv.prenom,
        date_naissance=inv.date_naissance,
        nss=inv.nss,
        societe=inv.entreprise,
        entreprise=inv.entreprise,
        dossier_sinistre=inv.dossier_sinistre,
        numero_mercer=inv.numero_contrat,
        partition=inv.partition,
        assureur=inv.assureur,
        patho=patho.libelle if patho else None,
        cim10=patho.code if patho else None,
        date_soumission=(inv.soumise_at or now).date(),
        **pl.champs_dossier(b),
    )
    db.add(d)
    db.flush()

    # Les fichiers déposés pendant le brouillon deviennent des documents du dossier
    for i, doc in enumerate(b["documents"]):
        f = db.get(Fichier, doc["fichier_id"])
        if not f or f.cible != CIBLE_PIECE or f.cible_id != inv.id:
            continue
        libelle = pl.PIECES.get(doc["categorie"], "Document")
        document = Document(dossier_id=d.id, nom=f"{libelle} — {doc['nom']}", type=doc.get("type") or "other",
                            taille=doc.get("taille"), position=i)
        db.add(document)
        db.flush()
        f.cible, f.cible_id = "document", document.id

    soumise = inv.soumise_at or now
    canal = {"sms": "SMS", "email": "email"}.get(inv.otp_canal or "", "code")
    evts = [
        (inv.envoyee_at or inv.created_at or soumise, "Invitation envoyée à l'assuré", inv.cree_par or "Système eCMD", "systeme"),
        (inv.identite_verifiee_at or soumise, f"Identité vérifiée (date de naissance + code {canal})",
         "Portail Certificat médical", "systeme"),
        (soumise, "Formulaire soumis par l'assuré", f"{inv.prenom} {inv.nom.title()} (Assuré)", "assure"),
    ]
    if b["documents"]:
        n = len(b["documents"])
        evts.append((soumise, f"Documents uploadés ({n} fichier{'s' if n > 1 else ''})", "Système eCMD", "systeme"))
    if get_settings().soumission_mode == "step_functions":
        evts.append((now, "Dossier créé (traitement de la soumission)", "AWS Step Functions", "systeme"))
    for dt, action, auteur, cat in evts:
        db.add(Evenement(dossier_id=d.id, date=dt, action=action, auteur=auteur, categorie=cat))

    obs = ((b.get("evolution") or {}).get("observations") or "").strip()
    if obs:
        db.add(Commentaire(dossier_id=d.id, date=soumise, auteur=f"{inv.prenom} {inv.nom.title()}", role="Assuré", texte=obs))

    db.add(DeclarationAssure(dossier_id=d.id, invitation_id=inv.id, reponses=b,
                             recapitulatif=pl.recapitulatif(admin_invitation(inv), b, libelles_pathologies(db))))
    inv.dossier_id = d.id
    log.info("Dossier %s créé pour l'invitation %s", d.id, inv.id)
    return d
