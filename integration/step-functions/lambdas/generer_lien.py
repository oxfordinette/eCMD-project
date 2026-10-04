"""Lambda « ecmd-generer-lien » : génère le lien d'invitation signé d'un sinistre.

Entrée (un élément envoyé par Databricks) : {"numero_sinistre", "prenom", "nom", "email", "type_certificat"}
Sortie : la même chose + {"lien", "expire_le"}

Le jeton ne contient que le n° de sinistre et une date d'expiration, signés avec le secret partagé avec le
backend eCMD (HMAC-SHA256). Même algorithme que cellmed/backend/app/liens.py : les deux doivent rester identiques.

Variables d'environnement :
  PORTAIL_URL            base du portail Certificat médical (ex. https://certificat.ecmd.fr)
  LIEN_DUREE_JOURS       validité du lien (défaut 30)
  SECRET_LIENS_ARN       secret AWS Secrets Manager contenant le secret (production)
  PORTAIL_SECRET_LIENS   secret en clair (LocalStack / tests uniquement)
"""
import base64
import hashlib
import hmac
import os
import re
import time

_NUMERO = re.compile(r"^[A-Za-z0-9-]{1,30}$")
_secret_cache = None


def _secret() -> str:
    global _secret_cache
    if _secret_cache is None:
        arn = os.environ.get("SECRET_LIENS_ARN")
        if arn:
            import boto3

            _secret_cache = boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]
        else:
            _secret_cache = os.environ.get("PORTAIL_SECRET_LIENS", "")
    if len(_secret_cache) < 32:
        raise RuntimeError("Secret des liens absent ou trop court (32 caractères minimum)")
    return _secret_cache


def _base36(n: int) -> str:
    chiffres = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = chiffres[r] + s
        if n == 0:
            return s


def jeton(secret: str, numero_sinistre: str, expire_le: int) -> str:
    message = f"{numero_sinistre}.{_base36(expire_le)}"
    mac = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()[:16]
    return f"{message}.{base64.urlsafe_b64encode(mac).decode().rstrip('=')}"


def handler(event, context):  # noqa: ANN001, ARG001
    numero = str(event.get("numero_sinistre", ""))
    if not _NUMERO.match(numero):
        raise ValueError(f"Numéro de sinistre invalide : {numero!r}")
    expire_le = int(time.time()) + int(os.environ.get("LIEN_DUREE_JOURS", "30")) * 86400
    base = os.environ.get("PORTAIL_URL", "http://localhost:8081").rstrip("/")
    lien = f"{base}/acces/{jeton(_secret(), numero, expire_le)}"
    print(f"{numero} : lien généré, valable jusqu'au {time.strftime('%d/%m/%Y', time.gmtime(expire_le))}")
    return {**event, "lien": lien, "expire_le": expire_le}
