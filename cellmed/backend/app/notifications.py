"""Envoi des emails et SMS.

NOTIF_MODE=dev : rien n'est envoyé, le message est écrit dans les logs du backend.
NOTIF_MODE=aws : email via Amazon SES, SMS via Amazon SNS. AWS_ENDPOINT_URL permet de pointer
vers LocalStack (ex: http://localstack:4566) pour les tests.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from .config import get_settings

log = logging.getLogger("cellmed.notifications")


class NotificationError(RuntimeError):
    pass


@lru_cache
def _client(service: str):  # noqa: ANN202
    import boto3

    s = get_settings()
    kwargs = {"region_name": s.aws_region}
    if s.aws_endpoint_url:
        kwargs["endpoint_url"] = s.aws_endpoint_url
    return boto3.client(service, **kwargs)


def envoyer_email(destinataire: str, sujet: str, texte: str) -> None:
    s = get_settings()
    if s.notif_mode != "aws":
        log.warning("[DEV] Email à %s — %s\n%s", destinataire, sujet, texte)
        return
    try:
        _client("ses").send_email(
            Source=s.ses_expediteur,
            Destination={"ToAddresses": [destinataire]},
            Message={
                "Subject": {"Data": sujet, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": texte, "Charset": "UTF-8"}},
            },
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Échec d'envoi de l'email à %s", destinataire)
        raise NotificationError("L'email n'a pas pu être envoyé") from e


def envoyer_sms(numero: str, texte: str) -> None:
    s = get_settings()
    numero = normaliser_telephone(numero)
    if s.notif_mode != "aws":
        log.warning("[DEV] SMS à %s — %s", numero, texte)
        return
    try:
        _client("sns").publish(
            PhoneNumber=numero,
            Message=texte,
            MessageAttributes={
                "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": s.sms_expediteur},
                "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"},
            },
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Échec d'envoi du SMS à %s", numero)
        raise NotificationError("Le SMS n'a pas pu être envoyé") from e


def preparer_aws() -> None:
    """En mode aws avec LocalStack : vérifie l'adresse d'expédition SES (requis par SES)."""
    s = get_settings()
    if s.notif_mode == "aws" and s.aws_endpoint_url:
        try:
            _client("ses").verify_email_identity(EmailAddress=s.ses_expediteur)
        except Exception:  # noqa: BLE001
            log.warning("Impossible de vérifier l'expéditeur SES %s", s.ses_expediteur)


def normaliser_telephone(numero: str) -> str:
    """'06 12 34 56 78' -> '+33612345678' (format E.164 attendu par SNS)."""
    chiffres = "".join(c for c in numero if c.isdigit() or c == "+")
    if chiffres.startswith("+"):
        return chiffres
    if chiffres.startswith("00"):
        return "+" + chiffres[2:]
    if chiffres.startswith("0") and len(chiffres) == 10:
        return "+33" + chiffres[1:]
    return chiffres


def masquer_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domaine = email.split("@", 1)
    return f"{local[:3]}••••@{domaine}"


def masquer_telephone(tel: str | None) -> str | None:
    if not tel:
        return None
    n = normaliser_telephone(tel)
    if n.startswith("+33") and len(n) == 12:
        return f"+33 {n[3]} •• •• •• {n[-2:]}"
    return f"•• •• •• {n[-2:]}"
