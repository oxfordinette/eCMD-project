"""Règles métier du formulaire « Certificat médical » (portail assuré).

Source unique pour : pièces justificatives exigées, validation des étapes, récapitulatif lisible
(affiché à l'assuré à l'étape 7 et dans la fiche CellMed) et création du dossier CellMed.

Structure du brouillon (JSON) :
    administratif: profession, college, adresse, email, telephone
    arret:        date_symptomes, date_debut, date_fin, cause (accident|maladie|grossesse),
                  type_accident (travail|vie_privee), tiers, maladie_pro, pathologie_code,
                  arret_anterieur, autres_pathologies [code]
    antecedents:  patho_avant, patho_anterieure, patho_consecutive, patho_consecutive_detail, ald, etat_sante
    soins:        traitements [{nom, posologie}], specialistes, specialiste_date, specialiste_motif,
                  hospitalisation, hospitalisation_date, hospitalisation_type
    evolution:    reprise, reprise_temps (partiel|plein), reprise_date, invalidite, invalidite_date,
                  invalidite_categorie, incapacite, incapacite_date, incapacite_taux, retraite,
                  retraite_date, observations
    documents:    [{fichier_id, categorie, nom, taille, type}]
Les réponses oui/non sont stockées "oui" / "non".
"""
from __future__ import annotations

from datetime import date

PIECES = {
    "cr_arret_initial": "Compte rendu de consultation - Arrêt de travail initial",
    "declaration_at": "Déclaration d'accident du travail",
    "cr_etat_sante": "Compte rendu de consultation - État de santé actuel",
    "ordonnance": "Traitement(s) - Ordonnance médicale",
    "cr_specialiste": "Tous les derniers comptes rendus de consultation - Médecin spécialiste",
    "cr_hospitalisation": "Compte rendu d'hospitalisation ou d'intervention chirurgicale",
    "notif_invalidite": "Notification de pension d'invalidité",
    "notif_ip": "Notification du taux d'incapacité permanente",
    "notif_retraite": "Notification de départ à la retraite",
    "autre": "Autre document (facultatif)",
}

CATEGORIES_INVALIDITE = {
    "1": "1ère catégorie — capable d'exercer une activité rémunérée",
    "2": "2e catégorie — incapable d'exercer une activité",
    "3": "3e catégorie — besoin de l'assistance d'une tierce personne",
}

ETAPES = {
    1: "Administratif",
    2: "Arrêt de travail",
    3: "Antécédents & état",
    4: "Soins & traitements",
    5: "Evolution & reprise",
    6: "Documents justificatifs",
    7: "Récapitulatif",
}


def _s(d: dict, k: str) -> dict:
    v = d.get(k)
    return v if isinstance(v, dict) else {}


def oui(v: object) -> bool:
    return v == "oui"


def traitements_saisis(b: dict) -> list[dict]:
    return [t for t in _s(b, "soins").get("traitements") or [] if (t or {}).get("nom", "").strip()]


def pieces_requises(b: dict) -> list[dict]:
    """Pièces exigées selon les réponses : [{categorie, libelle, etape, obligatoire}]."""
    a, s, e = _s(b, "arret"), _s(b, "soins"), _s(b, "evolution")
    out = [("cr_arret_initial", 2)]
    if a.get("cause") == "accident" and a.get("type_accident") == "travail":
        out.append(("declaration_at", 2))
    out.append(("cr_etat_sante", 3))
    if traitements_saisis(b):
        out.append(("ordonnance", 4))
    if oui(s.get("specialistes")):
        out.append(("cr_specialiste", 4))
    if oui(s.get("hospitalisation")):
        out.append(("cr_hospitalisation", 4))
    if oui(e.get("invalidite")):
        out.append(("notif_invalidite", 5))
    if oui(e.get("incapacite")):
        out.append(("notif_ip", 5))
    if oui(e.get("retraite")):
        out.append(("notif_retraite", 5))
    res = [{"categorie": c, "libelle": PIECES[c], "etape": et, "obligatoire": True} for c, et in out]
    res.append({"categorie": "autre", "libelle": PIECES["autre"], "etape": 6, "obligatoire": False})
    return res


# ── Validation ────────────────────────────────────────────────────────────


def _req(err: list, cond: bool, msg: str) -> None:
    if not cond:
        err.append(msg)


def _date_ok(v: object) -> bool:
    try:
        date.fromisoformat(str(v))
        return True
    except ValueError:
        return False


def erreurs_etape(b: dict, etape: int, pathologies_connues: set[str] | None = None) -> list[str]:
    err: list[str] = []
    if etape == 1:
        ad = _s(b, "administratif")
        _req(err, bool((ad.get("email") or "").strip() or (ad.get("telephone") or "").strip()),
             "Un email ou un téléphone est nécessaire")
    elif etape == 2:
        a = _s(b, "arret")
        _req(err, _date_ok(a.get("date_symptomes")), "Date des premiers symptômes")
        _req(err, _date_ok(a.get("date_debut")), "Date de début de l'arrêt de travail initial")
        if _date_ok(a.get("date_symptomes")) and _date_ok(a.get("date_debut")):
            _req(err, a["date_symptomes"] <= a["date_debut"],
                 "Les premiers symptômes doivent précéder le début de l'arrêt")
        if a.get("date_fin"):
            _req(err, _date_ok(a.get("date_fin")) and a["date_fin"] >= (a.get("date_debut") or ""),
                 "Date de fin prévisionnelle invalide")
        _req(err, a.get("cause") in ("accident", "maladie", "grossesse"), "Cause de l'arrêt de travail")
        if a.get("cause") == "accident":
            _req(err, a.get("type_accident") in ("travail", "vie_privee"), "Type d'accident")
            _req(err, a.get("tiers") in ("oui", "non"), "Accident causé par un tiers")
        if a.get("cause") == "maladie":
            _req(err, a.get("maladie_pro") in ("oui", "non"), "Maladie professionnelle")
        _req(err, bool(a.get("pathologie_code")), "Pathologie à l'origine de l'arrêt")
        if pathologies_connues is not None and a.get("pathologie_code"):
            _req(err, a["pathologie_code"] in pathologies_connues, "Pathologie inconnue")
        _req(err, a.get("arret_anterieur") in ("oui", "non"), "Précédent arrêt pour la même pathologie")
    elif etape == 3:
        an = _s(b, "antecedents")
        _req(err, an.get("patho_avant") in ("oui", "non"), "Pathologie avant cet arrêt")
        if oui(an.get("patho_avant")):
            _req(err, bool((an.get("patho_anterieure") or "").strip()), "Pathologie antérieure")
        _req(err, an.get("patho_consecutive") in ("oui", "non"), "Pathologie consécutive")
        if oui(an.get("patho_consecutive")):
            _req(err, bool((an.get("patho_consecutive_detail") or "").strip()), "Précisez la pathologie consécutive")
        _req(err, an.get("ald") in ("oui", "non"), "Prise en charge ALD")
        _req(err, bool((an.get("etat_sante") or "").strip()), "État de santé actuel")
    elif etape == 4:
        s = _s(b, "soins")
        for t in s.get("traitements") or []:
            if (t or {}).get("posologie", "").strip() and not (t or {}).get("nom", "").strip():
                err.append("Nom du traitement manquant")
                break
        _req(err, s.get("specialistes") in ("oui", "non"), "Suivi par un ou plusieurs spécialistes")
        if oui(s.get("specialistes")):
            _req(err, _date_ok(s.get("specialiste_date")), "Date de la dernière consultation")
            _req(err, bool((s.get("specialiste_motif") or "").strip()), "Motif de la dernière consultation")
        _req(err, s.get("hospitalisation") in ("oui", "non"), "Hospitalisation ou intervention chirurgicale")
        if oui(s.get("hospitalisation")):
            _req(err, _date_ok(s.get("hospitalisation_date")), "Date de l'hospitalisation")
            _req(err, bool((s.get("hospitalisation_type") or "").strip()), "Type d'hospitalisation")
    elif etape == 5:
        e = _s(b, "evolution")
        _req(err, e.get("reprise") in ("oui", "non"), "Reprise d'activité")
        if oui(e.get("reprise")):
            _req(err, e.get("reprise_temps") in ("partiel", "plein"), "Temps partiel ou plein")
            _req(err, _date_ok(e.get("reprise_date")), "Date de reprise effective")
        _req(err, e.get("invalidite") in ("oui", "non"), "Invalidité")
        if oui(e.get("invalidite")):
            _req(err, _date_ok(e.get("invalidite_date")), "Date de début d'invalidité")
            _req(err, e.get("invalidite_categorie") in CATEGORIES_INVALIDITE, "Catégorie d'invalidité")
        _req(err, e.get("incapacite") in ("oui", "non"), "Incapacité permanente")
        if oui(e.get("incapacite")):
            _req(err, _date_ok(e.get("incapacite_date")), "Date de début d'incapacité permanente")
            try:
                taux = float(e.get("incapacite_taux"))
                _req(err, 0 < taux <= 100, "Taux d'incapacité permanente (1 à 100 %)")
            except (TypeError, ValueError):
                err.append("Taux d'incapacité permanente (1 à 100 %)")
        _req(err, e.get("retraite") in ("oui", "non"), "Retraite")
        if oui(e.get("retraite")):
            _req(err, _date_ok(e.get("retraite_date")), "Date de début de retraite")
    elif etape == 6:
        fournies = {d.get("categorie") for d in b.get("documents") or []}
        for p in pieces_requises(b):
            if p["obligatoire"] and p["categorie"] not in fournies:
                err.append(p["libelle"])
    return err


def erreurs_formulaire(b: dict, pathologies_connues: set[str]) -> dict[int, list[str]]:
    out = {}
    for etape in range(1, 7):
        e = erreurs_etape(b, etape, pathologies_connues)
        if e:
            out[etape] = e
    return out


# ── Récapitulatif ─────────────────────────────────────────────────────────


def _d(v: object) -> str:
    try:
        return date.fromisoformat(str(v)).strftime("%d/%m/%Y")
    except ValueError:
        return "--"


def _on(v: object) -> str:
    return {"oui": "Oui", "non": "Non"}.get(str(v), "--")


def _t(v: object) -> str:
    v = (str(v) if v is not None else "").strip()
    return v or "--"


def recapitulatif(inv: dict, b: dict, libelles_patho: dict[str, str]) -> list[dict]:
    """Sections {numero, titre, etape, lignes:[{label, valeur}]} — valeur peut être une liste."""
    ad, a, an = _s(b, "administratif"), _s(b, "arret"), _s(b, "antecedents")
    s, e = _s(b, "soins"), _s(b, "evolution")

    def patho(code: str | None) -> str:
        return libelles_patho.get(code or "", code or "--")

    cause = {"accident": "Accident", "maladie": "Maladie", "grossesse": "État de grossesse"}.get(a.get("cause"), "--")
    l_arret = [
        ("Date de l'arrêt de travail", _d(a.get("date_debut"))),
        ("Date de fin prévisionnelle", _d(a.get("date_fin")) if a.get("date_fin") else "--"),
        ("Date des premiers symptômes", _d(a.get("date_symptomes"))),
        ("Cause de l'arrêt de travail", cause),
    ]
    if a.get("cause") == "accident":
        l_arret += [
            ("Type d'accident", {"travail": "Accident de travail", "vie_privee": "Accident de la vie privée"}.get(a.get("type_accident"), "--")),
            ("Causé par un tiers", _on(a.get("tiers"))),
        ]
    if a.get("cause") == "maladie":
        l_arret.append(("S'agit-il d'une maladie professionnelle ?", _on(a.get("maladie_pro"))))
    l_arret.append(("Pathologie à l'origine de l'arrêt de travail actuel", patho(a.get("pathologie_code"))))
    autres = [patho(c) for c in a.get("autres_pathologies") or [] if c]
    if autres:
        l_arret.append(("Autres pathologies à l'origine de l'arrêt", autres))
    l_arret.append(("Précédent arrêt de travail pour la même pathologie", _on(a.get("arret_anterieur"))))

    l_ant = [("Aviez-vous une pathologie avant cet arrêt", _on(an.get("patho_avant")))]
    if oui(an.get("patho_avant")):
        l_ant.append(("Pathologie antérieure", _t(an.get("patho_anterieure"))))
    l_ant.append(("Une autre pathologie consécutive est-elle apparue après le début de l'arrêt ?", _on(an.get("patho_consecutive"))))
    if oui(an.get("patho_consecutive")):
        l_ant.append(("Pathologie consécutive", _t(an.get("patho_consecutive_detail"))))
    l_ant += [
        ("Bénéficiez-vous d'une prise en charge à 100 % pour raison médicale par un organisme de sécurité sociale (ALD) ?", _on(an.get("ald"))),
        ("État de santé actuel", _t(an.get("etat_sante"))),
    ]

    trt = [f"{t['nom'].strip()} ({t['posologie'].strip()})" if t.get("posologie", "").strip() else t["nom"].strip()
           for t in traitements_saisis(b)]
    l_soins = [
        ("Traitement (en cours ou envisagé)", trt or "--"),
        ("Résultats des consultations auprès d'un médecin spécialiste",
         f"Dernière consultation le {_d(s.get('specialiste_date'))} — {_t(s.get('specialiste_motif'))}" if oui(s.get("specialistes")) else "--"),
        ("Hospitalisations ou interventions chirurgicales subies ou envisagées",
         f"{_t(s.get('hospitalisation_type'))} — le {_d(s.get('hospitalisation_date'))}" if oui(s.get("hospitalisation")) else "--"),
    ]

    l_evo = [("Reprise effective", _on(e.get("reprise")))]
    if oui(e.get("reprise")):
        l_evo += [
            ("Temps de reprise", {"partiel": "Temps partiel", "plein": "Temps plein"}.get(e.get("reprise_temps"), "--")),
            ("Date de reprise effective", _d(e.get("reprise_date"))),
        ]
    l_evo.append(("Invalidité", _on(e.get("invalidite"))))
    if oui(e.get("invalidite")):
        l_evo += [
            ("Date de début d'invalidité", _d(e.get("invalidite_date"))),
            ("Catégorie d'invalidité", CATEGORIES_INVALIDITE.get(e.get("invalidite_categorie"), "--")),
        ]
    l_evo.append(("Incapacité permanente", _on(e.get("incapacite"))))
    if oui(e.get("incapacite")):
        l_evo += [
            ("Date de début d'incapacité permanente", _d(e.get("incapacite_date"))),
            ("Taux d'incapacité permanente", f"{e.get('incapacite_taux')} %"),
        ]
    l_evo.append(("Retraite", _on(e.get("retraite"))))
    if oui(e.get("retraite")):
        l_evo.append(("Date de début de retraite", _d(e.get("retraite_date"))))
    l_evo.append(("Observations complémentaires", _t(e.get("observations"))))

    docs = b.get("documents") or []
    l_docs = [
        (PIECES.get(p["categorie"], p["categorie"]),
         [d.get("nom") for d in docs if d.get("categorie") == p["categorie"]] or "--")
        for p in pieces_requises(b)
        if p["obligatoire"] or any(d.get("categorie") == p["categorie"] for d in docs)
    ]

    l_admin = [
        ("Nom de l'entreprise", _t(inv.get("entreprise"))),
        ("Numéro de contrat", _t(inv.get("numero_contrat"))),
        ("Nom de l'assureur", _t(inv.get("assureur"))),
        ("Nom", _t((inv.get("nom") or "").upper())),
        ("Prénom", _t(inv.get("prenom"))),
        ("Date de naissance", _d(inv.get("date_naissance"))),
        ("Numéro de Sécurité sociale", _t(format_nss(inv.get("nss")))),
        ("Profession", _t(ad.get("profession"))),
        ("Catégorie socioprofessionnelle", _t(ad.get("college"))),
        ("Adresse", _t(ad.get("adresse"))),
        ("Email", _t(ad.get("email"))),
        ("Téléphone", _t(ad.get("telephone"))),
    ]

    sections = [
        (1, "Informations administratives", l_admin),
        (2, "Informations sur l'arrêt de travail", l_arret),
        (3, "Antécédents et état de santé actuel", l_ant),
        (4, "Soins et traitements", l_soins),
        (5, "Évolution et reprise envisagée", l_evo),
        (6, "Documents justificatifs", l_docs),
    ]
    return [
        {"numero": f"{n:02d}", "titre": t, "etape": n, "lignes": [{"label": k, "valeur": v} for k, v in lignes]}
        for n, t, lignes in sections
    ]


def format_nss(nss: str | None) -> str | None:
    if not nss:
        return nss
    n = "".join(c for c in nss if c.isalnum())
    if len(n) != 13 and len(n) != 15:
        return nss
    parts = [n[0], n[1:3], n[3:5], n[5:7], n[7:10], n[10:13]] + ([n[13:15]] if len(n) == 15 else [])
    return " ".join(parts)


# ── Correspondance vers le dossier CellMed ────────────────────────────────


def type_arret(a: dict) -> str:
    if a.get("cause") == "accident":
        return "Accident de travail" if a.get("type_accident") == "travail" else "Accident de la vie privée"
    if a.get("cause") == "grossesse":
        return "État de grossesse"
    return "Maladie professionnelle" if oui(a.get("maladie_pro")) else "Maladie non professionnelle"


def urgence(b: dict) -> str:
    a, s, e = _s(b, "arret"), _s(b, "soins"), _s(b, "evolution")
    if (a.get("cause") == "accident" and a.get("type_accident") == "travail") or oui(s.get("hospitalisation")) \
            or oui(e.get("invalidite")) or oui(e.get("incapacite")):
        return "Haute"
    if oui(s.get("specialistes")) or oui(_s(b, "antecedents").get("ald")):
        return "Moyenne"
    return "Basse"


def champs_dossier(b: dict) -> dict:
    """Champs du dossier CellMed alimentés par la déclaration."""
    ad, a, an, s, e = (_s(b, k) for k in ("administratif", "arret", "antecedents", "soins", "evolution"))
    debut = date.fromisoformat(a["date_debut"])
    fin = date.fromisoformat(a["date_fin"]) if a.get("date_fin") else None
    return {
        "profession": ad.get("profession") or None,
        "college": ad.get("college") or None,
        "adresse": ad.get("adresse") or None,
        "email": ad.get("email") or None,
        "telephone": ad.get("telephone") or None,
        "date_debut": debut,
        "date_fin": fin,
        "duree": (fin - debut).days + 1 if fin else None,
        "type_arret": type_arret(a),
        "temps_partiel": ("Oui — reprise à temps partiel" if oui(e.get("reprise")) and e.get("reprise_temps") == "partiel" else "Non"),
        "commentaire": (an.get("etat_sante") or "").strip() or None,
        "traitement": "\n".join(
            f"{t['nom'].strip()} ({t['posologie'].strip()})" if t.get("posologie", "").strip() else t["nom"].strip()
            for t in traitements_saisis(b)
        ) or None,
        "hospitalisation": _on(s.get("hospitalisation")),
        "arret_anterieur": _on(a.get("arret_anterieur")),
        "patho_anterieure": _on(an.get("patho_avant")),
        "patho_consecutive": _on(an.get("patho_consecutive")),
        "ald": _on(an.get("ald")),
        "urgence": urgence(b),
    }
