"""Schémas Pydantic exposés par l'API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentOut(_ORM):
    id: int
    nom: str
    type: str
    taille: str | None
    a_fichier: bool = False  # contenu réellement disponible (sinon : document de démonstration)


class EvenementOut(_ORM):
    id: int
    date: datetime
    action: str
    auteur: str
    categorie: str


class CommentaireOut(_ORM):
    id: int
    date: datetime
    auteur: str
    role: str | None
    texte: str


class PieceRequiseOut(_ORM):
    id: int
    nom: str
    statut: str
    nb_relances: int
    date_limite: date | None


class DossierResume(_ORM):
    id: str
    status: str
    pieces_statut: str | None
    urgence: str
    type: str
    nom: str
    prenom: str
    date_naissance: date | None
    societe: str | None
    patho: str | None
    cim10: str | None
    date_soumission: date | None


class DossierDetail(DossierResume):
    parcours: list[str]
    nss: str | None
    profession: str | None
    college: str | None
    telephone: str | None
    email: str | None
    adresse: str | None
    dossier_sinistre: str | None
    numero_mercer: str | None
    partition: str | None
    entreprise: str | None
    assureur: str | None
    date_debut: date | None
    date_fin: date | None
    type_arret: str | None
    type_cert: str | None
    duree: int | None
    temps_partiel: str | None
    commentaire: str | None
    traitement: str | None
    hospitalisation: str | None
    arret_anterieur: str | None
    patho_anterieure: str | None
    patho_consecutive: str | None
    ald: str | None
    analyse_compte_rendu: str | None
    analyse_duree_estimee: int | None
    decision: str | None
    duree_validee: int | None
    documents: list[DocumentOut]
    evenements: list[EvenementOut]
    commentaires: list[CommentaireOut]
    pieces_requises: list[PieceRequiseOut]
    declaration: list[dict] | None = None  # récapitulatif de la déclaration de l'assuré (portail)


class DossierList(BaseModel):
    total: int
    items: list[DossierResume]


# ── Entrées ───────────────────────────────────────────────────────────────


class CommentaireIn(BaseModel):
    texte: str = Field(min_length=1, max_length=5000)


class AnalyseIn(BaseModel):
    compte_rendu: str | None = None
    duree_estimee: int | None = Field(None, ge=0, le=3650)


class ValiderIn(BaseModel):
    type: Literal["validate"] = "validate"
    decision: str
    duree_validee: int | None = Field(None, ge=0, le=3650)
    commentaire: str | None = None


class PiecesIn(BaseModel):
    type: Literal["pieces"] = "pieces"
    pieces: list[str] = Field(min_length=1)
    message: str | None = None
    delai_jours: int = 14


class ExpertiseIn(BaseModel):
    type: Literal["expertise"] = "expertise"
    medecin_id: int
    type_expertise: str
    motif: str | None = None


class AvisIn(BaseModel):
    type: Literal["avis"] = "avis"
    medecin_id: int
    motif: str | None = None
    delai: str | None = None


ActionIn = ValiderIn | PiecesIn | ExpertiseIn | AvisIn


# ── Référentiels ──────────────────────────────────────────────────────────


class PathologieDocumentOut(_ORM):
    id: int
    nom: str
    type: str
    taille: str | None
    a_fichier: bool = False


class PathologieOut(_ORM):
    code: str
    groupe: str
    libelle: str
    categorie: str | None
    duree_std: int | None
    synonymes: str | None
    commentaire: str | None
    documents: list[PathologieDocumentOut]


class MedecinOut(_ORM):
    id: int
    nom: str
    specialite: str


class Referentiels(BaseModel):
    decisions: list[str]
    types_expertise: list[str]
    delais_pieces: list[int]
    delais_avis: list[str]
    medecins: list[MedecinOut]
    groupes: list[str]
    categories: list[str]


class Utilisateur(BaseModel):
    """Utilisateur courant (en-tête, auteur des actions)."""

    id: int | None = None
    nom: str
    role: str
    initiales: str
    email: str | None = None


# ── Pathologies (administration) ──────────────────────────────────────────


class PathologieResume(_ORM):
    code: str
    groupe: str
    libelle: str
    categorie: str | None
    duree_std: int | None
    synonymes: str | None
    nb_documents: int = 0


class PathologieIn(BaseModel):
    code: str = Field(min_length=1, max_length=10)
    groupe: str = Field(min_length=1)
    libelle: str = Field(min_length=1, max_length=200)
    categorie: str | None = None
    duree_std: int | None = Field(None, ge=0, le=3650)
    synonymes: str | None = None
    commentaire: str | None = None


class GroupeOut(BaseModel):
    groupe: str
    nb: int


# ── Utilisateurs (administration) ─────────────────────────────────────────


class UtilisateurOut(_ORM):
    id: int
    nom: str
    prenom: str
    nom_affiche: str | None
    titre: str | None
    email: str
    telephone: str | None
    role: str
    statut: str
    langue: str
    fuseau: str
    notif_valider: bool
    notif_pieces: bool
    notif_expertise: bool
    notif_resume: bool
    derniere_connexion: datetime | None


class UtilisateurIn(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["admin", "manager", "medecin", "gestionnaire"] = "gestionnaire"
    statut: Literal["actif", "inactif"] = "actif"


class ProfilIn(BaseModel):
    nom_affiche: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    telephone: str | None = None
    langue: Literal["fr", "en"] = "fr"
    fuseau: str = "Europe/Paris"


class PreferencesIn(BaseModel):
    notif_valider: bool | None = None
    notif_pieces: bool | None = None
    notif_expertise: bool | None = None
    notif_resume: bool | None = None


# ── Statistiques ──────────────────────────────────────────────────────────


class Statistiques(BaseModel):
    total: int
    en_cours: int
    duree_moyenne: int
    urgence_haute: int
    duree_traitement_moyenne: int
    par_statut: dict[str, int]
    par_urgence: dict[str, int]
    top_pathologies: list[tuple[str, int]]
