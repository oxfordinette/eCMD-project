"""Indicateurs de pilotage (vue Statistiques)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import STATUTS, Dossier, Evenement
from ..schemas import Statistiques

router = APIRouter(prefix="/api/statistiques", tags=["statistiques"])


@router.get("", response_model=Statistiques)
def statistiques(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Dossier)) or 0

    par_statut = {s: 0 for s in STATUTS}
    par_statut.update(dict(db.execute(select(Dossier.status, func.count()).group_by(Dossier.status)).all()))

    par_urgence = {u: 0 for u in ("Haute", "Moyenne", "Basse")}
    par_urgence.update(dict(db.execute(select(Dossier.urgence, func.count()).group_by(Dossier.urgence)).all()))

    duree_moy = db.scalar(select(func.avg(Dossier.duree))) or 0

    # Durée de traitement : de la soumission au dernier événement de l'historique
    dernier_evt = (
        select(Evenement.dossier_id, func.max(Evenement.date).label("derniere"))
        .group_by(Evenement.dossier_id)
        .subquery()
    )
    jours = func.extract("epoch", dernier_evt.c.derniere - func.cast(Dossier.date_soumission, dernier_evt.c.derniere.type)) / 86400
    traitement = db.scalar(
        select(func.avg(func.greatest(jours, 0)))
        .select_from(Dossier)
        .join(dernier_evt, dernier_evt.c.dossier_id == Dossier.id)
        .where(Dossier.date_soumission.is_not(None))
    ) or 0

    top = db.execute(
        select(Dossier.patho, func.count().label("n"))
        .where(Dossier.patho.is_not(None))
        .group_by(Dossier.patho)
        .order_by(func.count().desc(), Dossier.patho)
        .limit(8)
    ).all()

    return Statistiques(
        total=total,
        en_cours=total - par_statut.get("clotures", 0),
        duree_moyenne=round(float(duree_moy)),
        urgence_haute=par_urgence.get("Haute", 0),
        duree_traitement_moyenne=round(float(traitement)),
        par_statut=par_statut,
        par_urgence=par_urgence,
        top_pathologies=[(p, n) for p, n in top],
    )
