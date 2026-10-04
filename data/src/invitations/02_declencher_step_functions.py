# Databricks notebook source
# MAGIC %md
# MAGIC # Envoi des nouveaux sinistres à AWS Step Functions
# MAGIC
# MAGIC ```
# MAGIC gold.sinistre_prerempli ──► gold.nouveau_sinistre ──► Step Functions « ecmd-invitations-automatiques »
# MAGIC                               (éligibles, pas encore     (Lambda génère le lien signé → email SES)
# MAGIC                                transmis)
# MAGIC ```
# MAGIC
# MAGIC 1. **Suivi des envois précédents** : pour les exécutions Step Functions terminées, chaque sinistre passe de
# MAGIC    `transmis` à `envoye` ou `echec` dans `gold.sinistre_envoye`. Un échec est retenté au passage suivant
# MAGIC    (au plus `tentatives_max` fois).
# MAGIC 2. **Nouveaux sinistres** : la vue `gold.nouveau_sinistre` liste les sinistres éligibles jamais transmis (ou
# MAGIC    en échec). Ils sont envoyés par lots de 200 ; chaque exécution porte le n° du run Databricks.
# MAGIC 3. Un sinistre n'est marqué `transmis` que si AWS a accepté l'exécution.
# MAGIC
# MAGIC **Données transmises** : n° de sinistre, prénom, nom, email, type de certificat — rien d'autre (pas de NSS,
# MAGIC date de naissance ni adresse : le portail les relit dans Lakebase).
# MAGIC
# MAGIC **Modes** (`mode_declenchement`) :
# MAGIC - `journal` : affiche ce qui serait envoyé, sans appeler AWS ni rien marquer (dev sans compte AWS) ;
# MAGIC - `aws` : appel réel. Accès AWS par un **service credential** Unity Catalog (rôle IAM limité à
# MAGIC   `states:StartExecution` et `states:DescribeExecution` sur cette machine à états) ;
# MAGIC   avec `aws_endpoint_url` renseigné (LocalStack joignable par un tunnel), identifiants de test LocalStack.

# COMMAND ----------

import json
from datetime import datetime, timezone

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "ecmd_dev")
dbutils.widgets.dropdown("mode_declenchement", "journal", ["journal", "aws"])
dbutils.widgets.text("service_credential", "ecmd-aws-stepfunctions")
dbutils.widgets.text("state_machine_arn", "")
dbutils.widgets.text("aws_region", "eu-west-3")
dbutils.widgets.text("aws_endpoint_url", "")
dbutils.widgets.text("run_id", "manuel")
dbutils.widgets.text("tentatives_max", "3")

catalog = dbutils.widgets.get("catalog")
mode = dbutils.widgets.get("mode_declenchement")
credential = dbutils.widgets.get("service_credential")
sm_arn = dbutils.widgets.get("state_machine_arn").strip()
region = dbutils.widgets.get("aws_region")
endpoint = dbutils.widgets.get("aws_endpoint_url").strip() or None
run_id = dbutils.widgets.get("run_id") or "manuel"
tentatives_max = int(dbutils.widgets.get("tentatives_max"))

GOLD = f"`{catalog}`.gold"
ENVOYE = f"{GOLD}.sinistre_envoye"
LOT = 200

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {ENVOYE} (
        numero_sinistre STRING NOT NULL, statut STRING, tentatives INT, execution_arn STRING,
        transmis_le TIMESTAMP, maj_le TIMESTAMP, erreur STRING
    ) COMMENT 'Sinistres transmis à AWS Step Functions pour invitation (transmis → envoye | echec)'
""")
spark.sql(f"""
    CREATE OR REPLACE VIEW {GOLD}.nouveau_sinistre
    COMMENT 'Sinistres éligibles pas encore transmis à Step Functions (ou en échec, à retenter)'
    AS SELECT p.numero_sinistre, p.prenom, p.nom, p.email, p.type_certificat, p.date_debut_arret
    FROM {GOLD}.sinistre_prerempli p
    LEFT JOIN {ENVOYE} e ON e.numero_sinistre = p.numero_sinistre
    WHERE p.motif_non_eligible IS NULL
      AND (e.numero_sinistre IS NULL OR (e.statut = 'echec' AND e.tentatives < {tentatives_max}))
""")


def maj_envois(lignes: list[dict]) -> None:
    """MERGE des statuts dans gold.sinistre_envoye (une ligne par sinistre)."""
    if not lignes:
        return
    df = spark.createDataFrame(
        lignes, "numero_sinistre string, statut string, execution_arn string, erreur string, transmis boolean"
    ).withColumn("maintenant", F.current_timestamp())
    df.createOrReplaceTempView("_maj_envois")
    spark.sql(f"""
        MERGE INTO {ENVOYE} t USING _maj_envois s ON t.numero_sinistre = s.numero_sinistre
        WHEN MATCHED THEN UPDATE SET
            statut = s.statut, erreur = s.erreur, maj_le = s.maintenant,
            execution_arn = coalesce(s.execution_arn, t.execution_arn),
            tentatives = t.tentatives + CASE WHEN s.transmis THEN 1 ELSE 0 END,
            transmis_le = CASE WHEN s.transmis THEN s.maintenant ELSE t.transmis_le END
        WHEN NOT MATCHED THEN INSERT (numero_sinistre, statut, tentatives, execution_arn, transmis_le, maj_le, erreur)
            VALUES (s.numero_sinistre, s.statut, 1, s.execution_arn, s.maintenant, s.maintenant, s.erreur)
    """)


# COMMAND ----------

if mode == "journal":
    nouveaux = spark.table(f"{GOLD}.nouveau_sinistre")
    print(f"Mode journal : {nouveaux.count()} sinistre(s) seraient envoyés à Step Functions (rien n'est marqué).")
    display(nouveaux)
    dbutils.jobs.taskValues.set("nb_transmis", 0)
    dbutils.notebook.exit("journal")

if not sm_arn:
    raise ValueError("state_machine_arn est vide : renseigner la variable du bundle en mode aws")

import boto3  # noqa: E402

if endpoint:  # LocalStack (via tunnel) : identifiants de test
    sfn = boto3.client("stepfunctions", region_name=region, endpoint_url=endpoint,
                       aws_access_key_id="test", aws_secret_access_key="test")
else:
    session = boto3.Session(botocore_session=dbutils.credentials.getServiceCredentialsProvider(credential),
                            region_name=region)
    sfn = session.client("stepfunctions")

# COMMAND ----------

# 1. Résultat des exécutions précédentes
en_attente = [r.execution_arn for r in spark.sql(
    f"SELECT DISTINCT execution_arn FROM {ENVOYE} WHERE statut = 'transmis' AND execution_arn IS NOT NULL").collect()]
suivis = []
for arn in en_attente:
    ex = sfn.describe_execution(executionArn=arn)
    if ex["status"] == "RUNNING":
        continue
    numeros = [r.numero_sinistre for r in spark.sql(
        f"SELECT numero_sinistre FROM {ENVOYE} WHERE execution_arn = '{arn}' AND statut = 'transmis'").collect()]
    resultats = {}
    if ex["status"] == "SUCCEEDED":
        for r in json.loads(ex.get("output") or "{}").get("resultats", []):
            resultats[r.get("numero_sinistre")] = r
    for n in numeros:
        r = resultats.get(n)
        if r and r.get("statut") == "envoye":
            suivis.append(dict(numero_sinistre=n, statut="envoye", execution_arn=None, erreur=None, transmis=False))
        else:
            erreur = (r or {}).get("erreur") or f"exécution {ex['status']}"
            suivis.append(dict(numero_sinistre=n, statut="echec", execution_arn=None, erreur=str(erreur)[:500], transmis=False))
maj_envois(suivis)
print(f"Suivi : {sum(s['statut'] == 'envoye' for s in suivis)} envoyé(s), {sum(s['statut'] == 'echec' for s in suivis)} échec(s)")

# COMMAND ----------

# 2. Envoi des nouveaux sinistres
nouveaux = [r.asDict() for r in spark.table(f"{GOLD}.nouveau_sinistre").orderBy("date_debut_arret").collect()]
print(f"{len(nouveaux)} nouveau(x) sinistre(s) à transmettre")

transmis = 0
for i in range(0, len(nouveaux), LOT):
    lot = nouveaux[i:i + LOT]
    entree = {
        "origine": "databricks",
        "run_id": run_id,
        "transmis_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sinistres": [
            {k: (str(v) if v is not None else None) for k, v in s.items() if k != "date_debut_arret"} for s in lot
        ],
    }
    nom = f"ecmd-{run_id}-{i // LOT + 1}"[:80]
    try:
        arn = sfn.start_execution(stateMachineArn=sm_arn, name=nom, input=json.dumps(entree))["executionArn"]
    except sfn.exceptions.ExecutionAlreadyExists:
        # Tâche relancée dans le même run : l'exécution existe déjà, on ne renvoie pas
        arn = sm_arn.replace(":stateMachine:", ":execution:") + f":{nom}"
    maj_envois([dict(numero_sinistre=s["numero_sinistre"], statut="transmis", execution_arn=arn, erreur=None,
                     transmis=True) for s in lot])
    transmis += len(lot)
    print(f"✔ Lot {i // LOT + 1} : {len(lot)} sinistre(s) → {nom}")

dbutils.jobs.taskValues.set("nb_transmis", transmis)
print(f"Terminé : {transmis} sinistre(s) transmis à Step Functions")
