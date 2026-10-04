"""Lambdas de la machine à états « ecmd-soumission-certificat ».

  creer_dossier  : crée le dossier CellMed (tables cellmed de Lakebase) à partir de la déclaration soumise ;
  envoyer_accuse : envoie à l'assuré l'accusé de réception (SES) avec la référence du dossier.

Entrée : {"invitation_id": <id>} — seul l'identifiant circule dans Step Functions : la déclaration (données de
santé) est relue directement dans Lakebase et n'apparaît jamais dans l'historique des exécutions.

Le paquet `app` embarqué est une copie de cellmed/backend/app (config, db, models, portail_logic, soumission) :
la règle de création du dossier est la même que celle du backend (mode direct). Connexion à la base : mêmes
variables d'environnement que le backend (DB_MODE, LAKEBASE_*, DATABRICKS_*, DATABASE_URL, DB_SCHEMA).
"""
import logging
import os

logging.getLogger().setLevel(logging.INFO)
os.environ.setdefault("SOUMISSION_MODE", "step_functions")

from app.db import SessionLocal  # noqa: E402  (après la configuration de l'environnement)
from app.models import Invitation  # noqa: E402
from app.soumission import SoumissionInvalide, creer_dossier as _creer_dossier  # noqa: E402


class ErreurTemporaire(Exception):
    pass


def _invitation(db, event) -> Invitation:  # noqa: ANN001
    inv = db.get(Invitation, int(event["invitation_id"]))
    if inv is None:
        raise SoumissionInvalide(f"Invitation {event['invitation_id']} introuvable")
    return inv


def creer_dossier(event, context):  # noqa: ANN001, ARG001
    with SessionLocal() as db:
        inv = _invitation(db, event)
        d = _creer_dossier(db, inv)
        db.commit()
        print(f"Invitation {inv.id} : dossier {d.id}")
        return {"numero_dossier": d.id}


def envoyer_accuse(event, context):  # noqa: ANN001, ARG001
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    with SessionLocal() as db:
        inv = _invitation(db, event)
        email, prenom, nom, dossier_id = inv.email, inv.prenom, inv.nom, inv.dossier_id
    numero = (event.get("dossier") or {}).get("numero_dossier") or dossier_id
    if not email:
        return {"statut": "ignore", "motif": "aucun email"}
    salutation = f"Bonjour {prenom} {nom.title()},"
    texte = (
        f"{salutation}\n\nNous avons bien reçu votre attestation de certificat médical.\n\n"
        f"Référence de votre dossier : {numero}\n\n"
        "Votre dossier va être étudié par un gestionnaire. Vous serez informé(e) si des pièces complémentaires "
        "sont nécessaires.\n"
    )
    ses = boto3.client("ses", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
    try:
        r = ses.send_email(
            Source=os.environ.get("SES_EXPEDITEUR", "no-reply@cellmed.fr"),
            Destination={"ToAddresses": [email]},
            Message={"Subject": {"Data": f"Accusé de réception — dossier {numero}", "Charset": "UTF-8"},
                     "Body": {"Text": {"Data": texte, "Charset": "UTF-8"}}},
        )
    except ClientError as err:
        if err.response.get("Error", {}).get("Code") in {"Throttling", "ServiceUnavailable", "InternalFailure"}:
            raise ErreurTemporaire(str(err)) from err
        raise
    except BotoCoreError as err:
        raise ErreurTemporaire(str(err)) from err
    print(f"Accusé de réception envoyé ({email[:2]}***) pour le dossier {numero}")
    return {"statut": "envoye", "message_id": r["MessageId"]}
