"""Vérifie la connexion à Lakebase avec la configuration du .env.

Usage :
    docker compose run --rm backend python -m app.lakebase_check
ou, hors Docker (dans cellmed/backend avec le .env) :
    python -m app.lakebase_check
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from .config import get_settings


def main() -> int:
    s = get_settings()
    print(f"DB_MODE        : {s.db_mode}")
    if s.db_mode != "lakebase":
        print("⚠️  DB_MODE n'est pas 'lakebase' : rien à vérifier côté Databricks.")
        return 1

    try:
        from .db import engine
    except Exception as e:  # noqa: BLE001
        print(f"❌ Impossible de préparer la connexion : {e}")
        print("   Vérifie DATABRICKS_HOST et l'authentification (DATABRICKS_TOKEN ou client id/secret).")
        return 1

    print(f"Hôte Postgres  : {engine.url.host}")
    print(f"Base           : {engine.url.database}")
    print(f"Rôle Postgres  : {engine.url.username}")
    try:
        with engine.connect() as c:
            user = c.execute(text("select current_user")).scalar()
            version = c.execute(text("select version()")).scalar()
            can_create = c.execute(
                text("select has_database_privilege(current_user, current_database(), 'CREATE')")
            ).scalar()
            schema = c.execute(
                text("select count(*) from information_schema.schemata where schema_name = :s"), {"s": s.db_schema}
            ).scalar()
    except Exception as e:  # noqa: BLE001
        print(f"❌ Connexion refusée : {e}")
        print("   Si le message parle du rôle : crée un rôle Postgres pour cette identité dans le projet Lakebase.")
        return 1

    print(f"✅ Connecté en tant que {user}")
    print(f"   {version.split(',')[0]}")
    print(f"   Droit CREATE sur la base : {'oui' if can_create else 'NON (impossible de créer le schéma)'}")
    print(f"   Schéma '{s.db_schema}' : {'existe déjà' if schema else 'sera créé au démarrage'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
