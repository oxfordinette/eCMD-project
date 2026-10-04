"""API du portail assuré « Certificat médical ».

Accès en 4 étapes : lien d'invitation (token) → date de naissance → choix du canal → code à 6 chiffres.
Le code validé donne un jeton de session (en-tête Authorization: Bearer …) pour le formulaire.
"""
from __future__ import annotations

import hashlib
import json
import hmac
import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import liens, notifications, open_data, portail_logic as pl, soumission, storage
from ..config import get_settings
from ..db import get_db
from ..models import Fichier, Invitation, Pathologie

router = APIRouter(prefix="/api/portail", tags=["portail assuré"])
log = logging.getLogger("cellmed.portail")
CIBLE_PIECE = "invitation"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(v: str) -> str:
    return hashlib.sha256(v.encode()).hexdigest()


LIEN_INVALIDE = "Ce lien n'est pas valide. Contactez votre assureur."


def _invitation(db: Session, token: str) -> Invitation:
    """Retrouve l'invitation d'un lien.

    - Lien signé (envoyé automatiquement par AWS) : la signature est vérifiée, puis l'invitation est créée à la
      première ouverture à partir du sinistre Open (table gold synchronisée). Avant cette ouverture, rien n'existe
      dans la base de l'application : CellMed ne voit le sinistre qu'une fois le certificat soumis (dossier créé).
    - Autre jeton (invitation de démonstration) : recherche directe en base.
    """
    inv = db.scalar(select(Invitation).where(Invitation.token == token))
    if inv is None and liens.est_signe(token):
        inv = _invitation_depuis_lien(db, token)
    if not inv or inv.statut == "annulee":
        raise HTTPException(404, LIEN_INVALIDE)
    return inv


def _invitation_depuis_lien(db: Session, token: str) -> Invitation | None:
    try:
        lien = liens.verifier(get_settings().portail_secret_liens, token)
    except liens.LienExpire:
        raise HTTPException(410, "Ce lien a expiré. Contactez votre assureur pour en recevoir un nouveau.")
    except liens.LienInvalide:
        return None
    # Un même sinistre peut recevoir plusieurs liens (renvoi) : ils mènent tous à la même invitation
    inv = db.scalar(
        select(Invitation).where(Invitation.dossier_sinistre == lien.numero_sinistre).order_by(Invitation.id.desc())
    )
    if inv:
        return inv
    try:
        ligne = open_data.par_numero(db, lien.numero_sinistre)
    except HTTPException:
        log.error("Lien signé pour %s mais données Open indisponibles", lien.numero_sinistre)
        raise HTTPException(503, "Le service est momentanément indisponible. Merci de réessayer dans quelques minutes.")
    if not ligne or ligne.get("statut_sinistre") != "OUVERT":
        log.warning("Lien signé pour %s : sinistre introuvable ou clos", lien.numero_sinistre)
        return None
    inv = Invitation(
        **open_data.vers_invitation(ligne),
        token=token,
        statut="envoyee",
        cree_par="Invitation automatique (AWS)",
        envoyee_at=_now(),
        brouillon={},
    )
    db.add(inv)
    db.commit()
    log.info("Invitation %s créée à la première ouverture du lien (%s)", inv.id, lien.numero_sinistre)
    return inv


def session_assure(
    token: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Invitation:
    inv = _invitation(db, token)
    jeton = (authorization or "").removeprefix("Bearer ").strip()
    if (
        not jeton
        or not inv.session_hash
        or not hmac.compare_digest(inv.session_hash, _hash(jeton))
        or not inv.session_expire_at
        or inv.session_expire_at < _now()
    ):
        raise HTTPException(401, "Votre session a expiré. Merci de vous identifier à nouveau.")
    if inv.statut == "soumise":
        raise HTTPException(409, "Votre attestation a déjà été transmise.")
    return inv


# ── Accès ─────────────────────────────────────────────────────────────────


class EtatAcces(BaseModel):
    statut: str
    langue: str
    soumise: bool
    numero_dossier: str | None = None


@router.get("/{token}", response_model=EtatAcces)
def etat(token: str, db: Session = Depends(get_db)):
    inv = _invitation(db, token)
    return EtatAcces(statut=inv.statut, langue=inv.langue, soumise=inv.statut == "soumise", numero_dossier=inv.dossier_id)


class LangueIn(BaseModel):
    langue: Literal["fr", "en"]


@router.put("/{token}/langue", response_model=EtatAcces)
def choisir_langue(token: str, body: LangueIn, db: Session = Depends(get_db)):
    inv = _invitation(db, token)
    inv.langue = body.langue
    db.commit()
    return etat(token, db)


class IdentiteIn(BaseModel):
    date_naissance: date


class Canaux(BaseModel):
    sms: str | None
    email: str | None


@router.post("/{token}/identite", response_model=Canaux)
def verifier_identite(token: str, body: IdentiteIn, db: Session = Depends(get_db)):
    s = get_settings()
    inv = _invitation(db, token)
    if inv.statut == "soumise":
        raise HTTPException(409, "Votre attestation a déjà été transmise.")
    if inv.identite_essais >= s.identite_essais_max:
        raise HTTPException(423, "Trop de tentatives. Contactez votre assureur pour débloquer votre accès.")
    if body.date_naissance != inv.date_naissance:
        inv.identite_essais += 1
        db.commit()
        restants = max(0, s.identite_essais_max - inv.identite_essais)
        raise HTTPException(422, f"Les informations ne correspondent pas ({restants} essai(s) restant(s)).")
    inv.identite_essais = 0
    inv.identite_verifiee_at = _now()
    db.commit()
    return Canaux(sms=notifications.masquer_telephone(inv.telephone), email=notifications.masquer_email(inv.email))


class CodeIn(BaseModel):
    canal: Literal["sms", "email"]


class CodeOut(BaseModel):
    canal: str
    destination: str
    expire_min: int
    code_dev: str | None = None  # uniquement en mode dev


@router.post("/{token}/code", response_model=CodeOut)
def envoyer_code(token: str, body: CodeIn, db: Session = Depends(get_db)):
    s = get_settings()
    inv = _invitation(db, token)
    if not inv.identite_verifiee_at or inv.identite_verifiee_at < _now() - timedelta(minutes=30):
        raise HTTPException(403, "Vérifiez d'abord votre identité.")
    if inv.otp_expire_at and inv.otp_expire_at - timedelta(minutes=s.otp_duree_min) > _now() - timedelta(seconds=30):
        raise HTTPException(429, "Un code vient d'être envoyé. Patientez 30 secondes avant d'en demander un autre.")
    destination = inv.telephone if body.canal == "sms" else inv.email
    if not destination:
        raise HTTPException(422, "Aucune coordonnée disponible pour ce canal.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    texte = f"Votre code de vérification CellMed : {code}. Il est valable {s.otp_duree_min} minutes."
    try:
        if body.canal == "sms":
            notifications.envoyer_sms(destination, texte)
        else:
            notifications.envoyer_email(destination, "Votre code de vérification", texte)
    except notifications.NotificationError as e:
        raise HTTPException(502, str(e)) from e

    inv.otp_hash = _hash(f"{inv.token}:{code}")
    inv.otp_canal = body.canal
    inv.otp_expire_at = _now() + timedelta(minutes=s.otp_duree_min)
    inv.otp_essais = 0
    db.commit()
    masque = notifications.masquer_telephone(destination) if body.canal == "sms" else notifications.masquer_email(destination)
    return CodeOut(
        canal=body.canal,
        destination=masque or "",
        expire_min=s.otp_duree_min,
        code_dev=code if s.notif_mode != "aws" and s.portail_afficher_code_dev else None,
    )


class VerifierIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class SessionOut(BaseModel):
    session: str
    expire_at: datetime


@router.post("/{token}/verifier", response_model=SessionOut)
def verifier_code(token: str, body: VerifierIn, db: Session = Depends(get_db)):
    s = get_settings()
    inv = _invitation(db, token)
    if not inv.otp_hash or not inv.otp_expire_at or inv.otp_expire_at < _now():
        raise HTTPException(410, "Ce code a expiré. Demandez-en un nouveau.")
    if inv.otp_essais >= s.otp_essais_max:
        raise HTTPException(423, "Trop de tentatives. Demandez un nouveau code.")
    if not hmac.compare_digest(inv.otp_hash, _hash(f"{inv.token}:{body.code}")):
        inv.otp_essais += 1
        db.commit()
        raise HTTPException(422, "Code incorrect.")
    jeton = secrets.token_urlsafe(32)
    inv.session_hash = _hash(jeton)
    inv.session_expire_at = _now() + timedelta(minutes=s.session_duree_min)
    inv.otp_hash = None
    if inv.statut in ("creee", "envoyee"):
        inv.statut = "en_cours"
    db.commit()
    return SessionOut(session=jeton, expire_at=inv.session_expire_at)


# ── Formulaire ────────────────────────────────────────────────────────────


def _pathologies(db: Session) -> list[Pathologie]:
    return list(db.scalars(select(Pathologie).order_by(Pathologie.libelle)))


# Champs de l'invitation repris de la table gold sinistre_prerempli à l'ouverture du certificat
_CHAMPS_OPEN = ("type_certificat", "entreprise", "numero_contrat", "assureur", "partition", "nom", "prenom", "nss")
_CONTACTS_OPEN = ("profession", "college", "adresse", "email", "telephone")


def actualiser_depuis_open(db: Session, inv: Invitation) -> bool:
    """Relit le sinistre dans la table gold synchronisée (sinistre_prerempli) et met à jour l'invitation.

    Appelé quand l'assuré ouvre son certificat : les données affichées sont celles d'Open à cet instant,
    et non une copie figée au moment de l'invitation. Les coordonnées ne sont reprises que tant que
    l'assuré ne les a pas modifiées lui-même. La date de naissance (déjà vérifiée) n'est pas changée.
    Si la table Open est indisponible, on garde les données de l'invitation.
    """
    if not inv.dossier_sinistre or inv.statut == "soumise":
        return False
    try:
        with db.begin_nested():
            ligne = open_data.par_numero(db, inv.dossier_sinistre)
    except Exception as e:  # table non synchronisée, Lakebase indisponible… : on garde la copie de l'invitation
        log.warning("Données Open indisponibles pour %s : %s", inv.dossier_sinistre, getattr(e, "detail", e))
        return False
    if not ligne:
        return False
    champs = open_data.vers_invitation(ligne)
    modifie = False
    a_modifier = list(_CHAMPS_OPEN) + ([] if (inv.brouillon or {}).get("administratif") else list(_CONTACTS_OPEN))
    for c in a_modifier:
        v = champs.get(c)
        if v not in (None, "") and getattr(inv, c) != v:
            setattr(inv, c, v)
            modifie = True
    if modifie:
        db.commit()
        log.info("Invitation %s actualisée depuis Open (%s)", inv.id, inv.dossier_sinistre)
    return True


def _admin(inv: Invitation) -> dict:
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


def _brouillon_initial(inv: Invitation) -> dict:
    b = dict(inv.brouillon or {})
    b.setdefault(
        "administratif",
        {
            "profession": inv.profession or "",
            "college": inv.college or "",
            "adresse": inv.adresse or "",
            "email": inv.email or "",
            "telephone": inv.telephone or "",
        },
    )
    for section in ("arret", "antecedents", "soins", "evolution"):
        if not isinstance(b.get(section), dict):
            b[section] = {}
    b.setdefault("documents", [])
    return b


def _etat_formulaire(db: Session, inv: Invitation) -> dict:
    b = _brouillon_initial(inv)
    codes = {p.code for p in _pathologies(db)}
    return {
        "brouillon": b,
        "etape": inv.etape,
        "pieces_requises": pl.pieces_requises(b),
        "erreurs": {str(k): v for k, v in pl.erreurs_formulaire(b, codes).items()},
    }


@router.get("/{token}/formulaire")
def formulaire(inv: Invitation = Depends(session_assure), db: Session = Depends(get_db)):
    depuis_open = actualiser_depuis_open(db, inv)
    return {
        "admin": {**_admin(inv), "source": "open" if depuis_open else "invitation"},
        "pathologies": [{"code": p.code, "libelle": p.libelle, "groupe": p.groupe} for p in _pathologies(db)],
        "categories_invalidite": pl.CATEGORIES_INVALIDITE,
        **_etat_formulaire(db, inv),
    }


class BrouillonIn(BaseModel):
    brouillon: dict
    etape: int = Field(1, ge=1, le=7)


@router.put("/{token}/formulaire")
def enregistrer(body: BrouillonIn, inv: Invitation = Depends(session_assure), db: Session = Depends(get_db)):
    b = {k: v for k, v in body.brouillon.items() if k in ("administratif", "arret", "antecedents", "soins", "evolution")}
    b["documents"] = (inv.brouillon or {}).get("documents", [])  # gérés uniquement par les routes documents
    inv.brouillon = b
    inv.etape = body.etape
    db.commit()
    return _etat_formulaire(db, inv)


@router.post("/{token}/documents")
async def deposer(
    categorie: str = Form(...),
    fichier: UploadFile = File(...),
    inv: Invitation = Depends(session_assure),
    db: Session = Depends(get_db),
):
    if categorie not in pl.PIECES:
        raise HTTPException(422, "Catégorie de document inconnue")
    data, mime = await storage.lire_upload(fichier)
    if storage.type_document(fichier.filename or "") == "other":
        raise HTTPException(422, "Formats acceptés : JPEG, PNG, PDF")
    nom = fichier.filename or "document"
    f = storage.enregistrer(db, CIBLE_PIECE, inv.id, nom, mime, data)
    db.flush()
    b = _brouillon_initial(inv)
    b["documents"] = [
        *b["documents"],
        {"fichier_id": f.id, "categorie": categorie, "nom": nom, "taille": storage.taille_lisible(len(data)),
         "type": storage.type_document(nom)},
    ]
    inv.brouillon = b
    db.commit()
    return _etat_formulaire(db, inv)


@router.delete("/{token}/documents/{fichier_id}")
def retirer(fichier_id: int, inv: Invitation = Depends(session_assure), db: Session = Depends(get_db)):
    b = _brouillon_initial(inv)
    if not any(d["fichier_id"] == fichier_id for d in b["documents"]):
        raise HTTPException(404, "Document introuvable")
    f = db.get(Fichier, fichier_id)
    if f and f.cible == CIBLE_PIECE and f.cible_id == inv.id:
        storage.supprimer_fichier(db, f)
    b["documents"] = [d for d in b["documents"] if d["fichier_id"] != fichier_id]
    inv.brouillon = b
    db.commit()
    return _etat_formulaire(db, inv)


@router.get("/{token}/documents/{fichier_id}")
def voir(token: str, fichier_id: int, session: str | None = None, db: Session = Depends(get_db),
         authorization: str | None = Header(default=None)):
    # Le jeton peut être passé en paramètre pour un affichage dans un nouvel onglet
    inv = session_assure(token, authorization or (f"Bearer {session}" if session else None), db)
    f = db.get(Fichier, fichier_id)
    if not f or f.cible != CIBLE_PIECE or f.cible_id != inv.id:
        raise HTTPException(404, "Document introuvable")
    return Response(
        content=storage.lire(f),
        media_type=f.mime,
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(f.nom_fichier)}"},
    )


def _libelles_patho(db: Session) -> dict[str, str]:
    return {p.code: p.libelle for p in _pathologies(db)}


def _inv_dict(inv: Invitation) -> dict:
    return {**_admin(inv)}


@router.get("/{token}/recapitulatif")
def recap(inv: Invitation = Depends(session_assure), db: Session = Depends(get_db)):
    b = _brouillon_initial(inv)
    return {
        "sections": pl.recapitulatif(_inv_dict(inv), b, _libelles_patho(db)),
        "erreurs": {str(k): v for k, v in pl.erreurs_formulaire(b, set(_libelles_patho(db))).items()},
    }


def _demarrer_traitement(inv: Invitation) -> None:
    """Lance la machine à états « ecmd-soumission-certificat » : seul l'identifiant de l'invitation est transmis
    (aucune donnée de santé dans l'historique Step Functions). Le nom d'exécution rend l'appel idempotent."""
    import boto3

    s = get_settings()
    sfn = boto3.client("stepfunctions", region_name=s.aws_region, endpoint_url=s.aws_endpoint_url or None)
    try:
        sfn.start_execution(
            stateMachineArn=s.soumission_state_machine_arn,
            name=f"soumission-{inv.id}",
            input=json.dumps({"invitation_id": inv.id}),
        )
    except sfn.exceptions.ExecutionAlreadyExists:
        pass


@router.post("/{token}/soumettre")
def soumettre(inv: Invitation = Depends(session_assure), db: Session = Depends(get_db)):
    b = _brouillon_initial(inv)
    libelles = _libelles_patho(db)
    erreurs = pl.erreurs_formulaire(b, set(libelles))
    if erreurs:
        raise HTTPException(422, {"message": "Le formulaire est incomplet", "erreurs": {str(k): v for k, v in erreurs.items()}})

    # La déclaration est figée : plus de modification possible côté assuré
    inv.brouillon = b
    inv.statut = "soumise"
    inv.soumise_at = _now()
    inv.session_hash = None

    if get_settings().soumission_mode == "step_functions":
        db.commit()
        try:
            _demarrer_traitement(inv)
        except Exception as e:  # AWS indisponible : l'assuré pourra retransmettre
            log.error("Démarrage du traitement impossible pour l'invitation %s : %s", inv.id, e)
            inv.statut, inv.soumise_at = "en_cours", None
            db.commit()
            raise HTTPException(503, "La transmission n'a pas pu aboutir. Merci de réessayer dans quelques minutes.")
        log.info("Déclaration soumise : invitation %s, traitement confié à Step Functions", inv.id)
        return {"numero_dossier": None, "en_traitement": True}

    # Mode direct (développement sans AWS) : le dossier est créé immédiatement
    d = soumission.creer_dossier(db, inv)
    db.commit()
    log.info("Déclaration soumise : invitation %s → dossier %s", inv.id, d.id)
    return {"numero_dossier": d.id, "en_traitement": False}
