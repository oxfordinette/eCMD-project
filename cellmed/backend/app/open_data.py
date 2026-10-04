"""Accès aux données Open « gold » synchronisées depuis Databricks vers Lakebase.

La table (OPEN_TABLE, par défaut ecmd_gold.sinistre_prerempli) est une **table synchronisée** :
elle est créée et alimentée par Databricks à partir de <catalog>.gold.sinistre_prerempli
(voir data/README.md). L'application la lit uniquement.

Usage : le portail Certificat médical relit le sinistre à l'ouverture d'un lien d'invitation. Les opérateurs CellMed
n'y ont pas accès (un sinistre n'apparaît dans CellMed qu'une fois le certificat soumis).

En développement local (DB_MODE=postgres), une table de démonstration de même structure est créée.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings

log = logging.getLogger("cellmed.open")

# Contrat d'interface avec data/src/pipeline/gold/sinistre_prerempli.sql
COLONNES = [
    "numero_sinistre", "id_sinistre_open", "statut_sinistre", "nature_code", "type_arret", "date_declaration",
    "date_debut_arret", "type_certificat", "id_assure_open", "nss", "nom", "prenom", "date_naissance", "email",
    "telephone", "adresse", "profession", "numero_contrat", "assureur", "partition", "college", "entreprise",
    "siren", "date_maj_open", "motif_non_eligible", "calcule_le",
]


def _table() -> str:
    t = get_settings().open_table
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", t):
        raise RuntimeError(f"OPEN_TABLE invalide : {t}")
    return ".".join(f'"{p}"' for p in t.split("."))


def _demo_active() -> bool:
    s = get_settings()
    return s.open_demo if s.open_demo is not None else s.db_mode == "postgres"


def table_disponible(db: Session) -> bool:
    t = get_settings().open_table
    schema, _, nom = t.rpartition(".")
    return bool(db.scalar(
        text("SELECT count(*) FROM information_schema.tables WHERE table_name = :n AND (:s = '' OR table_schema = :s)"),
        {"n": nom, "s": schema},
    ))


def _verifier(db: Session) -> None:
    if not table_disponible(db):
        raise HTTPException(503, f"Les données Open ne sont pas encore synchronisées (table {get_settings().open_table} absente).")


def _lignes(db: Session, where: str, params: dict, limit: int = 50, order: str = "date_debut_arret DESC") -> list[dict]:
    _verifier(db)
    sql = f"SELECT {', '.join(COLONNES)} FROM {_table()} WHERE {where} ORDER BY {order} LIMIT :limit"
    return [dict(r._mapping) for r in db.execute(text(sql), {**params, "limit": limit})]


def rechercher(db: Session, q: str, limit: int = 20) -> list[dict]:  # dépannage / tests uniquement
    """Recherche par n° de sinistre, NSS, nom ou n° de contrat (opérateur CellMed)."""
    q = q.strip()
    if len(q) < 2:
        return []
    chiffres = re.sub(r"\D", "", q)
    return _lignes(
        db,
        "numero_sinistre ILIKE :like OR nom ILIKE :like OR prenom ILIKE :like OR numero_contrat ILIKE :like"
        " OR (:nss <> '' AND nss LIKE :nss)",
        {"like": f"%{q}%", "nss": f"{chiffres}%" if len(chiffres) >= 4 else ""},
        limit,
    )


def par_numero(db: Session, numero_sinistre: str) -> dict | None:
    r = _lignes(db, "numero_sinistre = :n", {"n": numero_sinistre}, 1)
    return r[0] if r else None


def vers_invitation(r: dict) -> dict:
    """Ligne gold → champs d'une invitation (informations administratives préremplies)."""
    return {
        "type_certificat": r.get("type_certificat") or "Initial",
        "entreprise": r.get("entreprise"),
        "numero_contrat": r.get("numero_contrat"),
        "assureur": r.get("assureur"),
        "partition": r.get("partition"),
        "dossier_sinistre": r["numero_sinistre"],
        "nom": r["nom"],
        "prenom": r["prenom"],
        "date_naissance": r["date_naissance"],
        "nss": r.get("nss"),
        "profession": r.get("profession"),
        "college": r.get("college"),
        "adresse": r.get("adresse"),
        "email": r.get("email"),
        "telephone": r.get("telephone"),
    }


# ── Table de démonstration (développement local) ─────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS {t} (
  numero_sinistre TEXT PRIMARY KEY, id_sinistre_open BIGINT, statut_sinistre TEXT, nature_code TEXT, type_arret TEXT,
  date_declaration DATE, date_debut_arret DATE, type_certificat TEXT, id_assure_open BIGINT, nss TEXT, nom TEXT,
  prenom TEXT, date_naissance DATE, email TEXT, telephone TEXT, adresse TEXT, profession TEXT, numero_contrat TEXT,
  assureur TEXT, partition TEXT, college TEXT, entreprise TEXT, siren TEXT, date_maj_open TIMESTAMPTZ,
  motif_non_eligible TEXT, calcule_le TIMESTAMPTZ
)"""


def preparer_demo(db: Session) -> None:
    if not _demo_active():
        return
    schema = get_settings().open_table.rpartition(".")[0]
    if schema:
        db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.execute(text(_DDL.format(t=_table())))
    if db.scalar(text(f"SELECT count(*) FROM {_table()}")):
        db.commit()
        return
    auj = date.today()
    now = datetime.now(timezone.utc)
    base = dict(statut_sinistre="OUVERT", nature_code="MAL", type_arret="Maladie non professionnelle",
                type_certificat="Initial", partition="MERCERAPPA", motif_non_eligible=None, date_maj_open=now, calcule_le=now)
    demo = [
        dict(numero_sinistre="SIN-2026-00001", id_sinistre_open=1, id_assure_open=1, nss="285047511004235", nom="DUPONT",
             prenom="Marie", date_naissance=date(1985, 4, 12), email="marie.dupont@entreprise.fr", telephone="+33612345647",
             adresse="12 rue des Lilas, 75011 Paris", profession="Ingénieur informatique", numero_contrat="AC-2024-001",
             assureur="AXA", college="Cadre", entreprise="Acme Groupe", siren="552100554",
             date_debut_arret=auj - timedelta(days=12), date_declaration=auj - timedelta(days=11)),
        dict(numero_sinistre="SIN-2026-00102", id_sinistre_open=102, id_assure_open=2, nss="190027511004255", nom="DURAND",
             prenom="Hugo", date_naissance=date(1990, 2, 15), email="hugo.durand@entreprise.fr", telephone="+33611223344",
             adresse="3 rue Oberkampf, 75011 Paris", profession="Comptable", numero_contrat="AC-2024-002",
             assureur="AXA", college="Non-cadre", entreprise="Acme Groupe", siren="552100554", nature_code="AT",
             type_arret="Accident de travail", date_debut_arret=auj - timedelta(days=3), date_declaration=auj - timedelta(days=2)),
        dict(numero_sinistre="SIN-2026-00103", id_sinistre_open=103, id_assure_open=3, nss="279117549449067", nom="MOREAU",
             prenom="Camille", date_naissance=date(1979, 11, 3), email="camille.moreau@entreprise.fr", telephone=None,
             adresse="8 avenue Victor Hugo, 31700 Blagnac", profession="Technicienne de production",
             numero_contrat="AIR-2022-007", assureur="Generali", college="Non-cadre", entreprise="Airbus France",
             siren="383474814", date_debut_arret=auj - timedelta(days=1), date_declaration=auj),
        dict(numero_sinistre="SIN-2026-00104", id_sinistre_open=104, id_assure_open=4, nss="274117549449067", nom="BERNARD",
             prenom="Emma", date_naissance=date(1974, 11, 21), email=None, telephone=None,
             adresse="5 impasse des Peupliers, 33000 Bordeaux", profession="Assistante RH", numero_contrat="ORG-2021-330",
             assureur="Allianz", college="Cadre", entreprise="Orange", siren="380129866",
             date_debut_arret=auj - timedelta(days=6), date_declaration=auj - timedelta(days=5),
             motif_non_eligible="Aucun email ni téléphone valide dans Open"),
        dict(numero_sinistre="SIN-2026-00090", id_sinistre_open=90, id_assure_open=5, nss="180057511002233", nom="PETIT",
             prenom="Nicolas", date_naissance=date(1980, 5, 9), email="nicolas.petit@entreprise.fr", telephone="+33689012345",
             adresse="78 rue Olivier de Serres, 75015 Paris", profession="Technicien réseau", numero_contrat="ORG-2021-330",
             assureur="Allianz", college="Cadre", entreprise="Orange", siren="380129866", statut_sinistre="CLOS",
             date_debut_arret=auj - timedelta(days=40), date_declaration=auj - timedelta(days=39),
             motif_non_eligible="Sinistre clos ou annulé"),
    ]
    cols = ", ".join(COLONNES)
    vals = ", ".join(f":{c}" for c in COLONNES)
    for r in demo:
        db.execute(text(f"INSERT INTO {_table()} ({cols}) VALUES ({vals})"), {c: {**base, **r}.get(c) for c in COLONNES})
    db.commit()
    log.info("Table Open de démonstration %s créée (%d sinistres)", get_settings().open_table, len(demo))
