"""Lambda « ecmd-envoyer-invitation » : envoie l'email d'invitation avec Amazon SES.

Entrée : {"numero_sinistre", "prenom", "nom", "email", "type_certificat", "lien", "expire_le"}
Sortie : {"numero_sinistre", "statut": "envoye", "message_id"}

Variables d'environnement :
  SES_EXPEDITEUR     adresse d'envoi vérifiée dans SES (ex. no-reply@cellmed.fr)
  AWS_ENDPOINT_URL   (LocalStack uniquement) ex. http://localstack:4566
Les erreurs passagères de SES (limitation de débit, indisponibilité) lèvent ErreurTemporaire : Step Functions réessaie.
"""
import html
import os
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class ErreurTemporaire(Exception):
    pass


_TEMPORAIRES = {"Throttling", "ThrottlingException", "TooManyRequestsException", "ServiceUnavailable", "InternalFailure"}
_ses = None


def _client():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
    return _ses


def message(event: dict) -> tuple[str, str, str]:
    prenom = (event.get("prenom") or "").strip()
    nom = (event.get("nom") or "").strip()
    salutation = f"Bonjour {prenom} {nom}".strip() + ","
    lien = event["lien"]
    date_fin = time.strftime("%d/%m/%Y", time.gmtime(int(event["expire_le"])))
    sujet = "Votre certificat médical à compléter"
    texte = (
        f"{salutation}\n\n"
        "Suite à votre arrêt de travail, votre assureur vous invite à compléter votre certificat médical en ligne.\n\n"
        f"Accédez au formulaire : {lien}\n\n"
        f"Ce lien est personnel et valable jusqu'au {date_fin}. Votre date de naissance puis un code de vérification "
        "vous seront demandés.\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n"
    )
    e = html.escape
    corps_html = f"""<div style="font-family:Arial,sans-serif;font-size:14px;color:#1e293b;max-width:560px">
<p>{e(salutation)}</p>
<p>Suite à votre arrêt de travail, votre assureur vous invite à compléter votre <strong>certificat médical</strong> en ligne.</p>
<p style="margin:24px 0"><a href="{e(lien)}" style="background:#1d4ed8;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:bold">Compléter mon certificat</a></p>
<p style="color:#64748b;font-size:12px">Ce lien est personnel et valable jusqu'au {date_fin}. Votre date de naissance puis un code de vérification vous seront demandés.<br>
Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.</p></div>"""
    return sujet, texte, corps_html


def handler(event, context):  # noqa: ANN001, ARG001
    numero = event["numero_sinistre"]
    destinataire = (event.get("email") or "").strip()
    if not destinataire:
        raise ValueError(f"{numero} : aucun email")
    sujet, texte, corps_html = message(event)
    try:
        r = _client().send_email(
            Source=os.environ.get("SES_EXPEDITEUR", "no-reply@cellmed.fr"),
            Destination={"ToAddresses": [destinataire]},
            Message={
                "Subject": {"Data": sujet, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": texte, "Charset": "UTF-8"}, "Html": {"Data": corps_html, "Charset": "UTF-8"}},
            },
        )
    except ClientError as err:
        code = err.response.get("Error", {}).get("Code", "")
        if code in _TEMPORAIRES:
            raise ErreurTemporaire(f"SES {code}") from err
        raise
    except BotoCoreError as err:  # réseau, délai dépassé
        raise ErreurTemporaire(str(err)) from err
    # L'email n'est jamais écrit en entier dans les journaux
    print(f"{numero} : invitation envoyée ({destinataire[:2]}***), message {r['MessageId']}")
    return {"numero_sinistre": numero, "statut": "envoye", "message_id": r["MessageId"]}
