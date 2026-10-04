"""Données de démonstration (reprises du mockup), chargées si la base est vide.

Usage manuel : python -m app.seed
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    Commentaire,
    Document,
    Dossier,
    Evenement,
    MedecinConseil,
    Pathologie,
    PathologieDocument,
    Invitation,
    PieceRequise,
    Utilisateur,
)

log = logging.getLogger(__name__)
PARIS = ZoneInfo("Europe/Paris")
DATA = Path(__file__).with_name("seed_data.json")

COULEUR_CATEGORIE = {
    "#64748b": "systeme",
    "#1d4ed8": "assure",
    "#c53532": "valider",
    "#d97706": "pieces",
    "#6d28d9": "expertise",
    "#0d9488": "avis-medical",
    "#14853d": "clotures",
}

MEDECINS = [
    ("Dr. Dupont", "Médecine générale"),
    ("Dr. Bernard", "Orthopédie"),
    ("Dr. Lefebvre", "Psychiatrie"),
    ("Dr. Rousseau", "Cardiologie"),
]


def _d(s: str | None) -> date | None:
    return datetime.strptime(s, "%d/%m/%Y").date() if s else None


def _dt(s: str) -> datetime:
    return datetime.strptime(s, "%d/%m/%Y %H:%M").replace(tzinfo=PARIS)


# (nom, prénom, nom affiché, titre, email, rôle, statut, téléphone, dernière connexion il y a N heures)
UTILISATEURS = [
    ("Martin", "", "Dr. Martin", "Gestionnaire Junior", "dr.martin@cellmed.fr", "gestionnaire", "actif", "01 42 56 78 90", 1),
    ("Martin", "Sophie", None, None, "s.martin@cellmed.fr", "medecin", "actif", None, 2),
    ("Lefèvre", "Antoine", None, None, "a.lefevre@cellmed.fr", "admin", "actif", None, 3),
    ("Rousseau", "Claire", None, None, "c.rousseau@cellmed.fr", "manager", "actif", None, 20),
    ("Durand", "Pierre", None, None, "p.durand@cellmed.fr", "gestionnaire", "actif", None, 26),
    ("Bernard", "Julie", None, None, "j.bernard@cellmed.fr", "gestionnaire", "inactif", None, 24 * 90),
    ("Dupont", "Marc", None, None, "m.dupont@cellmed.fr", "medecin", "actif", None, 4),
]


# Invitation de démonstration pour le portail Certificat médical (date de naissance : 12/04/1985)
INVITATION_DEMO = dict(
    token="demo-marie-dupont",
    statut="envoyee",
    type_certificat="Initial",
    entreprise="Acme Groupe",
    numero_contrat="AC-2024-001",
    assureur="AXA",
    partition="MERCERAPPA",
    dossier_sinistre="SIN-2026-00001",
    nom="Dupont",
    prenom="Marie",
    date_naissance=date(1985, 4, 12),
    nss="178047511004217",
    profession="Ingénieur informatique",
    college="Cadre",
    adresse="12 rue des Lilas, 75011 Paris",
    email="marie.dupont@entreprise.fr",
    telephone="+33 6 12 34 56 47",
    cree_par="Système eCMD",
)

# Pathologies utilisées dans les maquettes du portail assuré
PATHOLOGIES_COMPLEMENTAIRES = [
    ("J18.9", "Affections de l'appareil respiratoire", "Pneumonie", "Autre", 21, "Pneumopathie, Infection pulmonaire",
     "Infection pulmonaire aiguë. Arrêt selon gravité et terrain ; réévaluation à 3 semaines."),
    ("M18.9", "Affections Ostéo-Articulaires", "Rhizarthrose", "Ostéo-articulaire", 30, "Arthrose trapézo-métacarpienne",
     "Arthrose de la base du pouce. Arrêt selon le poste (travail manuel) et la prise en charge chirurgicale éventuelle."),
    ("C80.9", "Cancers", "Cancer", "Autre", 90, "Tumeur maligne, Néoplasie",
     "Tumeur maligne, localisation à préciser. Arrêts longs, réévaluation selon le protocole de traitement."),
]


def _completer_pathologies(db: Session) -> None:
    ajout = False
    for code, groupe, libelle, cat, duree, syn, com in PATHOLOGIES_COMPLEMENTAIRES:
        if not db.get(Pathologie, code):
            db.add(Pathologie(code=code, groupe=groupe, libelle=libelle, categorie=cat, duree_std=duree,
                              synonymes=syn, commentaire=com))
            ajout = True
    if ajout:
        db.commit()


def _vide(db: Session, model) -> bool:  # noqa: ANN001
    return not db.scalar(select(func.count()).select_from(model))


def seed_if_empty(db: Session) -> None:
    """Charge les données de démo table par table (n'écrase jamais des données existantes)."""
    data = json.loads(DATA.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)

    if _vide(db, Utilisateur):
        for nom, prenom, affiche, titre, email, role, statut, tel, h in UTILISATEURS:
            db.add(
                Utilisateur(
                    nom=nom, prenom=prenom, nom_affiche=affiche, titre=titre, email=email,
                    role=role, statut=statut, telephone=tel, derniere_connexion=now - timedelta(hours=h),
                )
            )
        db.commit()
        log.info("Utilisateurs de démonstration chargés")

    _completer_pathologies(db)
    if _vide(db, Invitation):
        db.add(Invitation(**INVITATION_DEMO, brouillon={}))
        db.commit()
        log.info("Invitation de démonstration créée : lien /acces/%s", INVITATION_DEMO["token"])

    if not _vide(db, Dossier):
        return

    if _vide(db, MedecinConseil):
        for nom, spe in MEDECINS:
            db.add(MedecinConseil(nom=nom, specialite=spe))

    existantes = set(db.scalars(select(Pathologie.code)))
    for p in data["pathologies"]:
        if p["code"] in existantes:
            continue
        db.add(
            Pathologie(
                code=p["code"],
                groupe=p["groupe"],
                libelle=p["libelle"],
                categorie=p.get("categorie"),
                duree_std=p.get("duree_std"),
                synonymes=p.get("synonymes"),
                commentaire=p.get("commentaire"),
                documents=[PathologieDocument(nom=x["name"], type=x["type"], taille=x["size"]) for x in p["docs"]],
            )
        )

    for x in data["dossiers"]:
        d = Dossier(
            id=x["id"],
            status=x["status"],
            pieces_statut=x.get("pieces_statut"),
            parcours=x.get("parcours") or [x["status"]],
            urgence=x["urgence"],
            type=x["type"],
            nom=x["nom"],
            prenom=x["prenom"],
            date_naissance=_d(x.get("dob")),
            nss=x.get("nss"),
            profession=x.get("profession"),
            college=x.get("college"),
            telephone=x.get("telephone"),
            email=x.get("email"),
            adresse=x.get("adresse"),
            societe=x.get("societe"),
            dossier_sinistre=x.get("dossier_sinistre"),
            numero_mercer=x.get("numero_mercer"),
            partition=x.get("partition"),
            entreprise=x.get("entreprise"),
            assureur=x.get("assureur"),
            date_debut=_d(x.get("debut")),
            date_fin=_d(x.get("fin")),
            type_arret=x.get("type_arret"),
            type_cert=x.get("type_cert"),
            duree=int(x["duree"]) if x.get("duree") else None,
            temps_partiel=x.get("temps_partiel"),
            patho=x.get("patho"),
            cim10=x.get("cim10"),
            commentaire=x.get("commentaire"),
            traitement=x.get("traitement"),
            hospitalisation=x.get("hospitalisation"),
            arret_anterieur=x.get("arret_anterieur"),
            patho_anterieure=x.get("patho_anterieure"),
            patho_consecutive=x.get("patho_consecutive"),
            ald=x.get("ald"),
            date_soumission=_d(x.get("soumission")),
        )
        d.documents = [
            Document(nom=doc["name"], type=doc["type"], taille=doc["size"], position=i)
            for i, doc in enumerate(x.get("docs", []))
        ]
        d.evenements = [
            Evenement(
                date=_dt(h["date"]),
                action=h["action"],
                auteur=h["auteur"],
                categorie=COULEUR_CATEGORIE.get(h.get("color", "").lower(), "systeme"),
            )
            for h in x.get("historique", [])
        ]
        d.commentaires = [
            Commentaire(date=_dt(c["date"]), auteur=c["auteur"], role=c.get("role"), texte=c["texte"])
            for c in x.get("commentaires", [])
        ]
        statut_piece = "recue" if x.get("pieces_statut") == "recues" else "attente"
        d.pieces_requises = [PieceRequise(nom=p["name"], statut=statut_piece) for p in x.get("pieces_requises", [])]
        db.add(d)

    db.commit()
    log.info("Données de démonstration chargées (%d dossiers)", len(data["dossiers"]))


if __name__ == "__main__":
    from .db import SessionLocal, init_db

    logging.basicConfig(level=logging.INFO)
    init_db()
    with SessionLocal() as s:
        seed_if_empty(s)
