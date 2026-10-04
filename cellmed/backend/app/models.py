"""Modèle de données CellMed (schéma `cellmed` dans Lakebase / Postgres)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import ARRAY, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Statuts du workflow (ordre = parcours affiché dans la frise)
STATUTS = ["valider", "pieces", "expertise", "avis-medical", "clotures"]


class Dossier(Base):
    __tablename__ = "dossier"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # ex: MQC-2024-00142
    status: Mapped[str] = mapped_column(String(20), index=True)
    pieces_statut: Mapped[str | None] = mapped_column(String(20))  # attente | recues
    parcours: Mapped[list[str]] = mapped_column(ARRAY(String(20)), default=list)
    urgence: Mapped[str] = mapped_column(String(10))  # Haute | Moyenne | Basse
    type: Mapped[str] = mapped_column(String(10))  # Initial | Suivi

    # Identité de l'assuré
    nom: Mapped[str] = mapped_column(String(100), index=True)
    prenom: Mapped[str] = mapped_column(String(100))
    date_naissance: Mapped[date | None] = mapped_column(Date)
    nss: Mapped[str | None] = mapped_column(String(15), index=True)
    profession: Mapped[str | None] = mapped_column(String(150))
    college: Mapped[str | None] = mapped_column(String(30))
    telephone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(200))
    adresse: Mapped[str | None] = mapped_column(String(300))
    societe: Mapped[str | None] = mapped_column(String(150))
    dossier_sinistre: Mapped[str | None] = mapped_column(String(32))

    # Contrat
    numero_mercer: Mapped[str | None] = mapped_column(String(32))
    partition: Mapped[str | None] = mapped_column(String(32))
    entreprise: Mapped[str | None] = mapped_column(String(150))
    assureur: Mapped[str | None] = mapped_column(String(100))

    # Arrêt de travail
    date_debut: Mapped[date | None] = mapped_column(Date)
    date_fin: Mapped[date | None] = mapped_column(Date)
    type_arret: Mapped[str | None] = mapped_column(String(60))
    type_cert: Mapped[str | None] = mapped_column(String(20))
    duree: Mapped[int | None] = mapped_column(Integer)
    temps_partiel: Mapped[str | None] = mapped_column(String(30))

    # Médical
    patho: Mapped[str | None] = mapped_column(String(200))
    cim10: Mapped[str | None] = mapped_column(String(10), index=True)
    commentaire: Mapped[str | None] = mapped_column(Text)  # état de santé
    traitement: Mapped[str | None] = mapped_column(Text)
    hospitalisation: Mapped[str | None] = mapped_column(String(10))
    arret_anterieur: Mapped[str | None] = mapped_column(String(10))
    patho_anterieure: Mapped[str | None] = mapped_column(String(10))
    patho_consecutive: Mapped[str | None] = mapped_column(String(10))
    ald: Mapped[str | None] = mapped_column(String(10))

    # Analyse du gestionnaire
    analyse_compte_rendu: Mapped[str | None] = mapped_column(Text)
    analyse_duree_estimee: Mapped[int | None] = mapped_column(Integer)
    decision: Mapped[str | None] = mapped_column(String(120))
    duree_validee: Mapped[int | None] = mapped_column(Integer)

    date_soumission: Mapped[date | None] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="Document.position"
    )
    evenements: Mapped[list[Evenement]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="Evenement.date"
    )
    commentaires: Mapped[list[Commentaire]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="Commentaire.date"
    )
    pieces_requises: Mapped[list[PieceRequise]] = relationship(
        back_populates="dossier", cascade="all, delete-orphan", order_by="PieceRequise.id"
    )


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossier.id", ondelete="CASCADE"), index=True)
    nom: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(10))  # pdf | img | other
    taille: Mapped[str | None] = mapped_column(String(20))
    chemin_stockage: Mapped[str | None] = mapped_column(String(500))  # futur : Volume Unity Catalog
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dossier: Mapped[Dossier] = relationship(back_populates="documents")


class Evenement(Base):
    """Historique du dossier."""

    __tablename__ = "evenement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossier.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(Text)
    auteur: Mapped[str] = mapped_column(String(150))
    # Catégorie d'événement, pilote la couleur : systeme | assure | valider | pieces | expertise | avis-medical | clotures
    categorie: Mapped[str] = mapped_column(String(20), default="systeme")

    dossier: Mapped[Dossier] = relationship(back_populates="evenements")


class Commentaire(Base):
    __tablename__ = "commentaire"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossier.id", ondelete="CASCADE"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    auteur: Mapped[str] = mapped_column(String(150))
    role: Mapped[str | None] = mapped_column(String(60))
    texte: Mapped[str] = mapped_column(Text)

    dossier: Mapped[Dossier] = relationship(back_populates="commentaires")


class PieceRequise(Base):
    __tablename__ = "piece_requise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossier.id", ondelete="CASCADE"), index=True)
    nom: Mapped[str] = mapped_column(String(255))
    statut: Mapped[str] = mapped_column(String(20), default="attente")  # attente | recue
    nb_relances: Mapped[int] = mapped_column(Integer, default=0)
    date_demande: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_limite: Mapped[date | None] = mapped_column(Date)

    dossier: Mapped[Dossier] = relationship(back_populates="pieces_requises")


# ── Référentiels ──────────────────────────────────────────────────────────


class Pathologie(Base):
    __tablename__ = "pathologie"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)  # CIM-10
    groupe: Mapped[str] = mapped_column(String(100), index=True)
    libelle: Mapped[str] = mapped_column(String(200))
    categorie: Mapped[str | None] = mapped_column(String(60))
    duree_std: Mapped[int | None] = mapped_column(Integer)
    synonymes: Mapped[str | None] = mapped_column(Text)
    commentaire: Mapped[str | None] = mapped_column(Text)

    documents: Mapped[list[PathologieDocument]] = relationship(
        back_populates="pathologie", cascade="all, delete-orphan", order_by="PathologieDocument.id"
    )


class PathologieDocument(Base):
    """Documents types associés à une pathologie (utilisés pour les demandes de pièces)."""

    __tablename__ = "pathologie_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pathologie_code: Mapped[str] = mapped_column(ForeignKey("pathologie.code", ondelete="CASCADE"), index=True)
    nom: Mapped[str] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(String(10))
    taille: Mapped[str | None] = mapped_column(String(20))

    pathologie: Mapped[Pathologie] = relationship(back_populates="documents")


class MedecinConseil(Base):
    __tablename__ = "medecin_conseil"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(150))
    specialite: Mapped[str] = mapped_column(String(100))
    actif: Mapped[bool] = mapped_column(default=True)


# ── Utilisateurs & préférences ────────────────────────────────────────────

ROLES = ["admin", "manager", "medecin", "gestionnaire"]


class Utilisateur(Base):
    __tablename__ = "utilisateur"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100), default="")
    nom_affiche: Mapped[str | None] = mapped_column(String(150))  # ex: "Dr. Martin"
    titre: Mapped[str | None] = mapped_column(String(100))  # ex: "Gestionnaire Junior"
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    telephone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(20), default="gestionnaire")  # admin | manager | medecin | gestionnaire
    statut: Mapped[str] = mapped_column(String(10), default="actif")  # actif | inactif
    langue: Mapped[str] = mapped_column(String(5), default="fr")
    fuseau: Mapped[str] = mapped_column(String(40), default="Europe/Paris")
    notif_valider: Mapped[bool] = mapped_column(default=True)
    notif_pieces: Mapped[bool] = mapped_column(default=True)
    notif_expertise: Mapped[bool] = mapped_column(default=True)
    notif_resume: Mapped[bool] = mapped_column(default=False)
    derniere_connexion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Fichiers (contenu des documents) ──────────────────────────────────────


class Fichier(Base):
    """Contenu binaire d'un document de dossier ou d'un document type de pathologie.

    Stocké soit directement dans Lakebase (colonne `contenu`), soit dans un Volume Unity Catalog
    (`chemin_volume`) selon STORAGE_MODE.
    """

    __tablename__ = "fichier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cible: Mapped[str] = mapped_column(String(20), index=True)  # document | pathologie_document
    cible_id: Mapped[int] = mapped_column(Integer, index=True)
    nom_fichier: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    taille_octets: Mapped[int] = mapped_column(Integer)
    contenu: Mapped[bytes | None] = mapped_column(LargeBinary)
    chemin_volume: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Portail assuré « Certificat médical » ─────────────────────────────────


class Invitation(Base):
    """Invitation envoyée à un assuré pour remplir son certificat médical.

    Porte les informations administratives pré-remplies, l'état de la vérification d'identité
    (date de naissance + code à usage unique), le brouillon du formulaire et, après soumission,
    le dossier CellMed créé.
    """

    __tablename__ = "invitation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    statut: Mapped[str] = mapped_column(String(20), default="creee")  # creee | envoyee | en_cours | soumise | annulee
    type_certificat: Mapped[str] = mapped_column(String(10), default="Initial")  # Initial | Suivi

    # Informations administratives (pré-remplies par l'opérateur / l'assureur)
    entreprise: Mapped[str | None] = mapped_column(String(150))
    numero_contrat: Mapped[str | None] = mapped_column(String(32))
    assureur: Mapped[str | None] = mapped_column(String(100))
    partition: Mapped[str | None] = mapped_column(String(32))
    dossier_sinistre: Mapped[str | None] = mapped_column(String(32))
    nom: Mapped[str] = mapped_column(String(100))
    prenom: Mapped[str] = mapped_column(String(100))
    date_naissance: Mapped[date] = mapped_column(Date)
    nss: Mapped[str | None] = mapped_column(String(15))
    profession: Mapped[str | None] = mapped_column(String(150))
    college: Mapped[str | None] = mapped_column(String(30))
    adresse: Mapped[str | None] = mapped_column(String(300))
    email: Mapped[str | None] = mapped_column(String(200))
    telephone: Mapped[str | None] = mapped_column(String(30))

    # Accès
    langue: Mapped[str] = mapped_column(String(5), default="fr")
    identite_essais: Mapped[int] = mapped_column(Integer, default=0)
    identite_verifiee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_hash: Mapped[str | None] = mapped_column(String(128))
    otp_canal: Mapped[str | None] = mapped_column(String(10))  # sms | email
    otp_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_essais: Mapped[int] = mapped_column(Integer, default=0)
    session_hash: Mapped[str | None] = mapped_column(String(128))
    session_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Formulaire
    brouillon: Mapped[dict] = mapped_column(JSONB, default=dict)
    etape: Mapped[int] = mapped_column(Integer, default=1)
    dossier_id: Mapped[str | None] = mapped_column(ForeignKey("dossier.id", ondelete="SET NULL"))

    cree_par: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    envoyee_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    soumise_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeclarationAssure(Base):
    """Déclaration complète de l'assuré, rattachée au dossier CellMed créé à la soumission."""

    __tablename__ = "declaration_assure"

    dossier_id: Mapped[str] = mapped_column(ForeignKey("dossier.id", ondelete="CASCADE"), primary_key=True)
    invitation_id: Mapped[int | None] = mapped_column(ForeignKey("invitation.id", ondelete="SET NULL"))
    reponses: Mapped[dict] = mapped_column(JSONB)  # réponses brutes du formulaire
    recapitulatif: Mapped[list] = mapped_column(JSONB)  # sections lisibles (identiques au récapitulatif)
    soumise_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
