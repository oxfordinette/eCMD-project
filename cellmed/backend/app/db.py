"""Connexion SQLAlchemy : Postgres classique ou Lakebase (Databricks)."""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import timezone

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import MetaData

from .config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    metadata = MetaData(schema=settings.db_schema)


def resolve_project_endpoint(w, project: str) -> tuple[str, str]:  # noqa: ANN001
    """Projet Lakebase (autoscaling) -> (endpoint lecture/écriture de la branche par défaut, hôte Postgres)."""
    from databricks.sdk.service.postgres import EndpointType

    # Accepte l'id du projet (projects/<id>), l'uid visible dans l'URL de l'interface, ou le nom affiché.
    wanted = project.removeprefix("projects/")
    projets = list(w.postgres.list_projects())
    match = next(
        (
            p
            for p in projets
            if wanted
            in {
                p.project_id,
                p.uid,
                (p.name or "").removeprefix("projects/"),
                getattr(p.status, "display_name", None),
                getattr(p.spec, "display_name", None),
            }
        ),
        None,
    )
    if match is None:
        dispo = ", ".join(
            f"{p.name} (uid={p.uid}, nom={getattr(p.status, 'display_name', None)})" for p in projets
        ) or "aucun projet visible pour cette identité"
        raise RuntimeError(f"Projet Lakebase '{project}' introuvable. Projets disponibles : {dispo}")
    parent = match.name
    branches = list(w.postgres.list_branches(parent=parent))
    if not branches:
        raise RuntimeError(f"Aucune branche dans le projet Lakebase {parent}")
    branch = next((b for b in branches if b.status and b.status.default), branches[0])
    endpoints = list(w.postgres.list_endpoints(parent=branch.name))
    rw = next(
        (e for e in endpoints if e.status and e.status.endpoint_type == EndpointType.ENDPOINT_TYPE_READ_WRITE),
        endpoints[0] if endpoints else None,
    )
    if rw is None:
        raise RuntimeError(f"Aucun endpoint dans la branche {branch.name}")
    host = rw.status.hosts.host if rw.status and rw.status.hosts else ""
    return rw.name, host


class _LakebaseTokenProvider:
    """Génère et met en cache le token OAuth utilisé comme mot de passe Postgres.

    Les tokens Lakebase expirent au bout d'une heure : on le renouvelle 10 minutes avant.
    """

    REFRESH_MARGIN_S = 600
    DEFAULT_TTL_S = 3600

    def __init__(self) -> None:
        from databricks.sdk import WorkspaceClient

        self._w = WorkspaceClient()
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0
        self.endpoint = settings.lakebase_endpoint
        self.host = settings.lakebase_host
        if settings.lakebase_project and not self.endpoint:
            self.endpoint, host = resolve_project_endpoint(self._w, settings.lakebase_project)
            self.host = self.host or host
        elif self.endpoint and not self.host:
            self.host = self._w.postgres.get_endpoint(self.endpoint).status.hosts.host
        if not self.host:
            raise RuntimeError("Mode lakebase : hôte Postgres introuvable, renseigner LAKEBASE_HOST")
        log.info("Lakebase : endpoint=%s host=%s", self.endpoint or settings.lakebase_instance_name, self.host)

    def username(self) -> str:
        if settings.lakebase_user:
            return settings.lakebase_user
        me = self._w.current_user.me()
        # Utilisateur humain -> email ; service principal -> application id
        return me.user_name or me.id

    def token(self) -> str:
        with self._lock:
            if self._token and time.time() < self._expires_at - self.REFRESH_MARGIN_S:
                return self._token
            if self.endpoint:
                cred = self._w.postgres.generate_database_credential(endpoint=self.endpoint)
            elif settings.lakebase_instance_name:
                cred = self._w.database.generate_database_credential(
                    request_id=str(uuid.uuid4()),
                    instance_names=[settings.lakebase_instance_name],
                )
            else:
                raise RuntimeError(
                    "Mode lakebase : renseigner LAKEBASE_PROJECT, LAKEBASE_ENDPOINT ou LAKEBASE_INSTANCE_NAME"
                )
            self._token = cred.token
            self._expires_at = time.time() + self.DEFAULT_TTL_S
            exp = getattr(cred, "expire_time", None)
            if exp is not None:
                try:
                    self._expires_at = exp.ToDatetime(tzinfo=timezone.utc).timestamp()
                except AttributeError:
                    pass
            log.info("Token Lakebase renouvelé")
            return self._token


def _build_engine() -> Engine:
    if settings.db_mode == "lakebase":
        provider = _LakebaseTokenProvider()
        url = URL.create(
            "postgresql+psycopg",
            username=provider.username(),
            host=provider.host,
            port=settings.lakebase_port,
            database=settings.lakebase_database,
            query={"sslmode": "require"},
        )
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800, pool_size=5, max_overflow=5)

        @event.listens_for(engine, "do_connect")
        def _inject_token(dialect, conn_rec, cargs, cparams):  # noqa: ANN001
            cparams["password"] = provider.token()

        return engine

    return create_engine(settings.database_url, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (enregistre les tables)

    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
    Base.metadata.create_all(engine)
