# Databricks notebook source
# MAGIC %md
# MAGIC # Simulateur de la base Open
# MAGIC
# MAGIC Alimente `<catalog>.open_sim` avec des tables au format supposé d'Open, pour développer
# MAGIC le pipeline sans accès à la vraie base :
# MAGIC
# MAGIC | Table Open | Contenu |
# MAGIC |---|---|
# MAGIC | `ENTREPRISE` | Entreprises clientes |
# MAGIC | `CONTRAT` | Contrats prévoyance (n° de contrat, assureur, partition, collège) |
# MAGIC | `ASSURE` | Assurés (identité, NSS, coordonnées) |
# MAGIC | `SINISTRE` | Sinistres / arrêts de travail déclarés |
# MAGIC
# MAGIC - **1er passage** : crée les tables avec un jeu de données (dont quelques défauts de qualité volontaires).
# MAGIC - **Passages suivants** : simule l'activité d'Open — nouveaux sinistres, changement d'adresse, sinistre clos.
# MAGIC
# MAGIC ⚠️ Ne jamais exécuter en production : la vraie source est la base Open (voir README).

# COMMAND ----------

import random
from datetime import date, datetime, timedelta

from pyspark.sql import Row

dbutils.widgets.text("catalog", "ecmd_dev")
catalog = dbutils.widgets.get("catalog")
SCHEMA = f"`{catalog}`.`open_sim`"


def existe(table: str) -> bool:
    return spark.catalog.tableExists(f"{catalog}.open_sim.{table}")


# COMMAND ----------

# MAGIC %md ## Jeu de données initial

# COMMAND ----------

ENTREPRISES = [
    (1, "ACME GROUPE", "552100554"),
    (2, "FNAC DARTY", "055800296"),
    (3, "AIRBUS FRANCE", "383474814"),
    (4, "SOCIETE GENERALE", "552120222"),
    (5, "ORANGE", "380129866"),
]
CONTRATS = [
    (101, "AC-2024-001", 1, "AXA", "MERCERAPPA", "CADRE"),
    (102, "AC-2024-002", 1, "AXA", "MERCERAPPA", "NON CADRE"),
    (103, "FD-2023-114", 2, "GENERALI", "MERCERAPPA", "NON CADRE"),
    (104, "AIR-2022-007", 3, "GENERALI", "MERCERAPPA", "NON CADRE"),
    (105, "SG-2024-045", 4, "AXA FRANCE", "MERCERPREV", "CADRE"),
    (106, "ORG-2021-330", 5, "ALLIANZ", "MERCERAPPA", "CADRE"),
]
PRENOMS = ["Marie", "Léa", "Hugo", "Paul", "Camille", "Thomas", "Inès", "Lucas", "Chloé", "Nicolas",
           "Sarah", "Julien", "Emma", "Karim", "Manon", "Antoine", "Lina", "Mathis", "Jade", "Yanis"]
NOMS = ["DUPONT", "DURAND", "MOREAU", "GARNIER", "LEROY", "DUBOIS", "BENALI", "PETIT", "FONTAINE", "ROUSSEAU",
        "MARTIN", "BERNARD", "THOMAS", "ROBERT", "RICHARD", "SIMON", "LAURENT", "MICHEL", "LEFEBVRE", "MERCIER"]
PROFESSIONS = ["Ingénieur informatique", "Comptable", "Technicien de maintenance", "Chargée de clientèle",
               "Opérateur de production", "Responsable marketing", "Chef d'équipe logistique", "Assistante RH"]
VILLES = [("75011", "PARIS"), ("92100", "BOULOGNE-BILLANCOURT"), ("31700", "BLAGNAC"), ("69003", "LYON"),
          ("13008", "MARSEILLE"), ("33000", "BORDEAUX")]


def nss(sexe: int, naissance: date, rnd: random.Random) -> str:
    base = f"{sexe}{naissance:%y}{naissance:%m}{rnd.choice(['75', '92', '31', '69'])}{rnd.randint(100, 999)}{rnd.randint(100, 999)}"
    cle = 97 - int(base) % 97
    return f"{base}{cle:02d}"


def assures_initiaux(rnd: random.Random) -> list[Row]:
    rows = []
    for i in range(1, 41):
        prenom, nom = PRENOMS[(i - 1) % 20], NOMS[(i * 7) % 20]
        sexe = 2 if prenom in {"Marie", "Léa", "Camille", "Inès", "Chloé", "Sarah", "Emma", "Manon", "Lina", "Jade"} else 1
        naissance = date(1965 + rnd.randint(0, 35), rnd.randint(1, 12), rnd.randint(1, 28))
        cp, ville = rnd.choice(VILLES)
        email = f"{prenom.lower().replace('é', 'e').replace('è', 'e')}.{nom.lower()}@entreprise.fr"
        tel = f"06{rnd.randint(10000000, 99999999)}"
        # Défauts de qualité volontaires (formats hétérogènes, données manquantes)
        if i % 9 == 0:
            tel = f"+33 6 {tel[2:4]} {tel[4:6]} {tel[6:8]} {tel[8:]}"
        if i % 11 == 0:
            email = email.upper()
        if i % 13 == 0:
            email, tel = None, None          # assuré injoignable → non éligible à l'invitation
        num_ss = nss(sexe, naissance, rnd)
        if i == 17:
            num_ss = "12345"                 # NSS invalide → quarantaine
        rows.append(Row(
            ID_ASSURE=i, NUM_SS=num_ss, NOM=nom, PRENOM=prenom, DATE_NAISSANCE=naissance, SEXE=str(sexe),
            EMAIL=email, TEL_MOBILE=tel, ADRESSE_1=f"{rnd.randint(1, 120)} rue des Lilas",
            CODE_POSTAL=cp, VILLE=ville, PROFESSION=rnd.choice(PROFESSIONS), ID_CONTRAT=CONTRATS[i % 6][0],
            DATE_MAJ=datetime.now() - timedelta(days=rnd.randint(30, 400)),
        ))
    # Assurée des maquettes du portail (date de naissance 12/04/1985)
    rows[0] = rows[0].asDict() | dict(
        NUM_SS="285047511004235", NOM="DUPONT", PRENOM="Marie", DATE_NAISSANCE=date(1985, 4, 12), SEXE="2",
        EMAIL="marie.dupont@entreprise.fr", TEL_MOBILE="0612345647", ADRESSE_1="12 rue des Lilas",
        CODE_POSTAL="75011", VILLE="PARIS", PROFESSION="Ingénieur informatique", ID_CONTRAT=101,
    )
    rows[0] = Row(**rows[0])
    return rows


NATURES = ["MAL", "MAL", "MAL", "AT", "MP", "MAT"]


def sinistre(id_sin: int, id_assure: int, id_contrat: int, debut: date, rnd: random.Random, statut: str = "O") -> Row:
    return Row(
        ID_SINISTRE=id_sin, NUM_SINISTRE=f"SIN-{debut.year}-{id_sin:05d}", ID_ASSURE=id_assure, ID_CONTRAT=id_contrat,
        DATE_DECLARATION=debut + timedelta(days=rnd.randint(0, 3)), DATE_DEBUT_ARRET=debut,
        CODE_NATURE=rnd.choice(NATURES), STATUT=statut, DATE_MAJ=datetime.now(),
    )


def creer_initial() -> None:
    rnd = random.Random(42)
    now = datetime.now()
    spark.createDataFrame([Row(ID_ENTREPRISE=i, RAISON_SOCIALE=r, SIREN=s, DATE_MAJ=now - timedelta(days=500))
                           for i, r, s in ENTREPRISES]).write.mode("overwrite").saveAsTable(f"{SCHEMA}.ENTREPRISE")
    spark.createDataFrame([Row(ID_CONTRAT=i, NUM_CONTRAT=n, ID_ENTREPRISE=e, ASSUREUR=a, PARTITION=p, COLLEGE=c,
                               DATE_EFFET=date(2021, 1, 1), DATE_RESILIATION=None, DATE_MAJ=now - timedelta(days=200))
                           for i, n, e, a, p, c in CONTRATS],
                          "ID_CONTRAT long, NUM_CONTRAT string, ID_ENTREPRISE long, ASSUREUR string, PARTITION string, "
                          "COLLEGE string, DATE_EFFET date, DATE_RESILIATION date, DATE_MAJ timestamp"
                          ).write.mode("overwrite").saveAsTable(f"{SCHEMA}.CONTRAT")
    assures = assures_initiaux(rnd)
    spark.createDataFrame(assures).write.mode("overwrite").saveAsTable(f"{SCHEMA}.ASSURE")
    sinistres = []
    for k, a in enumerate(assures[:24], start=1):
        debut = date.today() - timedelta(days=rnd.randint(2, 150))
        statut = "C" if k % 6 == 0 else "O"
        sinistres.append(sinistre(k, a.ID_ASSURE, a.ID_CONTRAT, debut, rnd, statut))
    spark.createDataFrame(sinistres).write.mode("overwrite").saveAsTable(f"{SCHEMA}.SINISTRE")
    print(f"Open simulé créé : {len(ENTREPRISES)} entreprises, {len(CONTRATS)} contrats, {len(assures)} assurés, {len(sinistres)} sinistres")


# COMMAND ----------

# MAGIC %md ## Activité simulée (passages suivants)

# COMMAND ----------


def simuler_activite() -> None:
    rnd = random.Random()
    max_sin = spark.sql(f"SELECT max(ID_SINISTRE) m FROM {SCHEMA}.SINISTRE").first().m or 0
    assures = spark.sql(f"SELECT ID_ASSURE, ID_CONTRAT FROM {SCHEMA}.ASSURE").collect()

    # 1) Deux nouveaux sinistres (arrêts récents)
    nouveaux = [sinistre(max_sin + k, a.ID_ASSURE, a.ID_CONTRAT, date.today() - timedelta(days=rnd.randint(0, 5)), rnd)
                for k, a in enumerate(rnd.sample(assures, 2), start=1)]
    spark.createDataFrame(nouveaux).write.mode("append").saveAsTable(f"{SCHEMA}.SINISTRE")

    # 2) Un assuré déménage (→ nouvelle version SCD2 en silver)
    a = rnd.choice(assures)
    cp, ville = rnd.choice(VILLES)
    spark.sql(f"""
        UPDATE {SCHEMA}.ASSURE
        SET ADRESSE_1 = '{rnd.randint(1, 120)} avenue Victor Hugo', CODE_POSTAL = '{cp}', VILLE = '{ville}',
            DATE_MAJ = current_timestamp()
        WHERE ID_ASSURE = {a.ID_ASSURE}""")

    # 3) Un sinistre ouvert est clos
    spark.sql(f"""
        UPDATE {SCHEMA}.SINISTRE SET STATUT = 'C', DATE_MAJ = current_timestamp()
        WHERE ID_SINISTRE = (SELECT min(ID_SINISTRE) FROM {SCHEMA}.SINISTRE WHERE STATUT = 'O' AND ID_SINISTRE > 1)""")
    print(f"Activité simulée : sinistres {[n.NUM_SINISTRE for n in nouveaux]} créés, assuré {a.ID_ASSURE} a déménagé, 1 sinistre clos")


# COMMAND ----------

if all(existe(t) for t in ("entreprise", "contrat", "assure", "sinistre")):
    simuler_activite()
else:
    creer_initial()
