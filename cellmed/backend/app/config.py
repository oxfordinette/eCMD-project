"""Configuration du backend CellMed (variables d'environnement / fichier .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Mode de connexion à la base ───────────────────────────────────────
    # "postgres" : DATABASE_URL classique (Postgres local de dev)
    # "lakebase" : Lakebase Databricks, mot de passe = token OAuth renouvelé
    db_mode: str = "postgres"

    # Mode postgres
    database_url: str = "postgresql+psycopg://cellmed:cellmed@localhost:5432/cellmed"

    # Mode lakebase
    # L'authentification Databricks est lue par le SDK depuis l'environnement :
    # DATABRICKS_HOST + (DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET) ou DATABRICKS_TOKEN
    lakebase_host: str = ""  # optionnel en mode projet/endpoint (résolu automatiquement)
    lakebase_port: int = 5432
    lakebase_database: str = "databricks_postgres"
    lakebase_user: str = ""  # vide = identité Databricks courante (email ou client id du SP)
    # Renseigner UN des trois :
    lakebase_project: str = ""  # Lakebase autoscaling : id du projet (branche par défaut, endpoint R/W)
    lakebase_endpoint: str = ""  # Lakebase autoscaling : projects/<p>/branches/<b>/endpoints/<e>
    lakebase_instance_name: str = ""  # Lakebase "provisioned" (database instance)

    db_schema: str = "cellmed"
    seed_on_startup: bool = True

    # ── Stockage des fichiers ─────────────────────────────────────────────
    # "db"     : contenu stocké dans Lakebase (table fichier)
    # "volume" : contenu stocké dans un Volume Unity Catalog (UC_VOLUME_PATH)
    storage_mode: str = "db"
    uc_volume_path: str = ""  # ex: /Volumes/cellmed/documents/fichiers
    max_upload_mo: int = 10

    # ── Portail assuré « Certificat médical » ─────────────────────────────
    portail_url: str = "http://localhost:8081"  # base des liens d'invitation
    otp_duree_min: int = 10
    otp_essais_max: int = 5
    identite_essais_max: int = 5
    session_duree_min: int = 120
    # En mode dev, le code est aussi renvoyé à l'écran (jamais en mode aws)
    portail_afficher_code_dev: bool = True

    # ── Données Open (gold, synchronisées depuis Databricks) ───────────────
    # Table synchronisée dans Lakebase depuis <catalog>.gold.sinistre_prerempli (schéma.table Postgres)
    open_table: str = "ecmd_gold.sinistre_prerempli"
    # Crée et alimente une table de démonstration au démarrage. Par défaut : seulement en DB_MODE=postgres
    # (en Lakebase, la table est créée et alimentée par la synchronisation Databricks)
    open_demo: bool | None = None
    # Secret partagé avec la Lambda « generer_lien » (AWS) pour vérifier les liens d'invitation signés.
    # Vide = seules les invitations de démonstration (jeton enregistré en base) fonctionnent.
    portail_secret_liens: str = ""
    # Soumission du certificat : « direct » = le backend crée le dossier (dev sans AWS) ;
    # « step_functions » = la machine à états ecmd-soumission-certificat le crée (Lambda ecmd-creer-dossier)
    soumission_mode: str = "direct"
    soumission_state_machine_arn: str = "arn:aws:states:eu-west-3:000000000000:stateMachine:ecmd-soumission-certificat"

    # ── Notifications (email / SMS) ───────────────────────────────────────
    # "dev" : rien n'est envoyé, le message est écrit dans les logs du backend
    # "aws" : email via Amazon SES, SMS via Amazon SNS (compatible LocalStack)
    notif_mode: str = "dev"
    aws_region: str = "eu-west-3"
    aws_endpoint_url: str = ""  # ex: http://localstack:4566 ; vide = AWS réel
    ses_expediteur: str = "no-reply@cellmed.fr"
    sms_expediteur: str = "CellMed"

    # ── Utilisateur courant (en attendant le SSO) ─────────────────────────
    # Le compte est cherché par email dans la table utilisateur (créé au besoin).
    default_user_email: str = "dr.martin@cellmed.fr"
    default_user_name: str = "Dr. Martin"
    default_user_role: str = "Gestionnaire Junior"

    cors_origins: str = "http://localhost:5173,http://localhost:5174"


@lru_cache
def get_settings() -> Settings:
    return Settings()
