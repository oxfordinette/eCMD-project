from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import current_user, marquer_connexion
from ..db import get_db
from ..models import MedecinConseil
from ..schemas import MedecinOut, Referentiels, Utilisateur

router = APIRouter(prefix="/api", tags=["référentiels"])

DECISIONS = [
    "ITT justifiée, jusqu'à fin d'arrêt",
    "ITT justifiée, jusqu'à date",
    "ITT justifiée, pendant mi-temps",
    "ITT justifiée, jusqu'au congés maternité",
    "ITT justifiée, suite reprise",
    "ITT justifiée, jusqu'à l'invalidité",
    "ITT justifiée, jusqu'à sortie des effectifs",
    "ITT justifiée, jusqu'à la retraite",
    "ITT tant que l'IJ est à 0€",
]
TYPES_EXPERTISE = ["Expertise sur dossier", "Expertise avec convocation", "Télé-expertise"]
DELAIS_PIECES = [7, 14, 21, 30]
DELAIS_AVIS = ["48 heures", "5 jours ouvrés", "10 jours ouvrés"]

PATHO_GROUPES = [
    "Affections allergiques",
    "Affections cardio-vasculaires",
    "Affections de l'appareil digestif",
    "Affections de l'appareil génital",
    "Affections de l'appareil respiratoire",
    "Affections de l'appareil urinaire",
    "Affections dermatologiques",
    "Affections endocriniennes",
    "Affections néphrologique",
    "Affections neurologiques",
    "Affections OPH",
    "Affections ORL",
    "Affections Ostéo-Articulaires",
    "Affections psychiatriques",
    "Autres",
    "Cancers",
    "Maladie du sang",
    "Maladies infectieuses",
]
PATHO_CATEGORIES = [
    "Ostéo-articulaire",
    "Psychiatrique",
    "Cardiologique",
    "Neurologique",
    "Gastro-entérologique",
    "Autre",
]


@router.get("/me", response_model=Utilisateur)
def me(user: Utilisateur = Depends(current_user), db: Session = Depends(get_db)):
    if user.id:
        marquer_connexion(db, user.id)
    return user


@router.get("/referentiels", response_model=Referentiels)
def referentiels(db: Session = Depends(get_db)):
    medecins = db.scalars(select(MedecinConseil).where(MedecinConseil.actif).order_by(MedecinConseil.nom)).all()
    return Referentiels(
        decisions=DECISIONS,
        types_expertise=TYPES_EXPERTISE,
        delais_pieces=DELAIS_PIECES,
        delais_avis=DELAIS_AVIS,
        medecins=[MedecinOut.model_validate(m) for m in medecins],
        groupes=PATHO_GROUPES,
        categories=PATHO_CATEGORIES,
    )
