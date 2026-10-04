"""Liens d'invitation signés (générés par AWS Lambda, vérifiés par le backend).

Format du jeton :  <numero_sinistre>.<expiration en base 36>.<signature>
  - expiration : horodatage Unix (secondes), en base 36 pour rester court ;
  - signature  : HMAC-SHA256(secret, "<numero_sinistre>.<expiration>"), 16 premiers octets, base64url sans « = ».
Exemple : SIN-2026-00001.tlx8k0.q3Jk9wQ0l2mZp4hTt7cX1A

Le secret (PORTAIL_SECRET_LIENS) est partagé entre la Lambda « generer_lien » et le backend, jamais avec Databricks.
Sans le secret, impossible de fabriquer un lien valide ; le jeton ne contient aucune donnée personnelle.
Même algorithme : integration/step-functions/lambdas/generer_lien.py (tests croisés dans le README).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from dataclasses import dataclass

_FORMAT = re.compile(r"^([A-Za-z0-9-]{1,30})\.([0-9a-z]{1,10})\.([A-Za-z0-9_-]{22})$")


class LienInvalide(Exception):
    pass


class LienExpire(Exception):
    pass


@dataclass(frozen=True)
class Lien:
    numero_sinistre: str
    expire_le: int


def _base36(n: int) -> str:
    chiffres = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = chiffres[r] + s
        if n == 0:
            return s


def _signature(secret: str, message: str) -> str:
    mac = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(mac).decode().rstrip("=")


def generer(secret: str, numero_sinistre: str, duree_jours: int = 30, maintenant: int | None = None) -> str:
    """Utilisé pour les tests et le dépannage ; en production, c'est la Lambda qui génère les liens."""
    exp = _base36((maintenant or int(time.time())) + duree_jours * 86400)
    message = f"{numero_sinistre}.{exp}"
    return f"{message}.{_signature(secret, message)}"


def est_signe(token: str) -> bool:
    return bool(_FORMAT.match(token))


def verifier(secret: str, token: str, maintenant: int | None = None) -> Lien:
    m = _FORMAT.match(token)
    if not m or not secret:
        raise LienInvalide()
    numero, exp36, sig = m.groups()
    if not hmac.compare_digest(sig, _signature(secret, f"{numero}.{exp36}")):
        raise LienInvalide()
    expire_le = int(exp36, 36)
    if expire_le < (maintenant or int(time.time())):
        raise LienExpire()
    return Lien(numero, expire_le)
