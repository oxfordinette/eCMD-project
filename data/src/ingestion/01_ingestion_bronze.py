# Databricks notebook source
# MAGIC %md
# MAGIC # Ingestion Open (SQL Server) → bronze
# MAGIC
# MAGIC Copie **incrémentale** des tables Open dans `<catalog>.bronze` : à chaque passage, seules les lignes
# MAGIC dont `DATE_MAJ` est postérieure au dernier chargement sont lues. Les tables bronze sont en **ajout seul**
# MAGIC (chaque version d'une ligne est conservée) : elles sont l'historique brut et rejouable de la source.
# MAGIC
# MAGIC Deux façons de lire Open :
# MAGIC - **`table`** (recommandé) : catalogue **Lakehouse Federation** sur la base SQL Server d'Open
# MAGIC   (ex. `open_fed.dbo`, voir `src/federation/connexion_open.sql`), ou le simulateur (`<catalog>.open_sim`).
# MAGIC   Le filtre `DATE_MAJ > …` est poussé vers SQL Server.
# MAGIC - **`jdbc`** : connexion JDBC directe (pilote Microsoft inclus dans le runtime Databricks). Hôte, base et
# MAGIC   identifiants sont lus dans le secret scope (`host`, `port`, `database`, `user`, `password`).
# MAGIC
# MAGIC **Recouvrement** : une transaction Open validée tardivement peut porter une `DATE_MAJ` antérieure au dernier
# MAGIC chargement. On relit donc les `recouvrement_minutes` précédentes, et les versions déjà présentes en bronze
# MAGIC (même clé + même `DATE_MAJ`) sont écartées : pas de perte, pas de doublon.
# MAGIC
# MAGIC Colonnes techniques ajoutées : `_ingere_le`, `_source`, `_lot_id`.

# COMMAND ----------

import uuid
from datetime import datetime

from pyspark.sql import functions as F

dbutils.widgets.text("catalog", "ecmd_dev")
dbutils.widgets.text("source_open", "ecmd_dev.open_sim")
dbutils.widgets.dropdown("mode_source", "table", ["table", "jdbc"])
dbutils.widgets.text("secret_scope", "ecmd-open")
dbutils.widgets.text("schema_sqlserver", "dbo")
dbutils.widgets.text("recouvrement_minutes", "10")
dbutils.widgets.dropdown("rechargement_complet", "false", ["false", "true"])

catalog = dbutils.widgets.get("catalog")
source_open = dbutils.widgets.get("source_open")
mode_source = dbutils.widgets.get("mode_source")
secret_scope = dbutils.widgets.get("secret_scope")
schema_sqlserver = dbutils.widgets.get("schema_sqlserver")
recouvrement = int(dbutils.widgets.get("recouvrement_minutes") or 0)
complet = dbutils.widgets.get("rechargement_complet") == "true"
lot_id = str(uuid.uuid4())

# Les DATETIME2 SQL Server n'ont pas de fuseau : on les relit « tels quels » en travaillant en UTC partout
# (même fuseau que la JVM des clusters Databricks), pour que le filtre incrémental compare des heures identiques.
spark.conf.set("spark.sql.session.timeZone", "UTC")

# Tables Open à copier : (table source, table bronze, colonne de suivi des modifications, clé)
TABLES = [
    ("ENTREPRISE", "open_entreprise", "DATE_MAJ", "ID_ENTREPRISE"),
    ("CONTRAT", "open_contrat", "DATE_MAJ", "ID_CONTRAT"),
    ("ASSURE", "open_assure", "DATE_MAJ", "ID_ASSURE"),
    ("SINISTRE", "open_sinistre", "DATE_MAJ", "ID_SINISTRE"),
]
JOURNAL = f"`{catalog}`.bronze._journal_ingestion"
FORMAT_TS = "yyyy-MM-dd HH:mm:ss.SSSSSS"

# COMMAND ----------


def _secret(cle: str, defaut: str | None = None) -> str:
    try:
        return dbutils.secrets.get(secret_scope, cle)
    except Exception:
        if defaut is None:
            raise
        return defaut


def options_jdbc() -> dict:
    """Connexion SQL Server à partir du secret scope (mêmes secrets que la connexion Lakehouse Federation)."""
    url = (
        f"jdbc:sqlserver://{_secret('host')}:{_secret('port', '1433')};"
        f"databaseName={_secret('database')};encrypt=true;"
        f"trustServerCertificate={_secret('trust_server_certificate', 'false')};"
        "loginTimeout=30;applicationName=ecmd-databricks"
    )
    return {
        "url": url,
        "user": _secret("user"),
        "password": _secret("password"),
        "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver",
        "fetchsize": "10000",
    }


def lire_source(table: str, col_maj: str, cle: str, depuis: str | None):
    """Lit la table Open, filtrée sur les lignes modifiées après `depuis` (texte 'yyyy-MM-dd HH:mm:ss.ffffff')."""
    if mode_source == "jdbc":
        opts = options_jdbc()
        nom = f"[{schema_sqlserver}].[{table}]"
        if depuis:
            # Littéral T-SQL (SQL Server ne connaît pas TIMESTAMP '…') ; DATETIME2(7) couvre DATETIME et DATETIME2
            requete = f"SELECT * FROM {nom} WHERE [{col_maj}] > CAST('{depuis}' AS DATETIME2(7))"
            return spark.read.format("jdbc").options(**opts).option("query", requete).load()
        # Chargement initial : lecture parallèle découpée sur la clé numérique
        bornes = (
            spark.read.format("jdbc").options(**opts)
            .option("query", f"SELECT MIN([{cle}]) AS mini, MAX([{cle}]) AS maxi FROM {nom}")
            .load().first()
        )
        lecteur = spark.read.format("jdbc").options(**opts).option("dbtable", nom)
        if bornes and bornes.mini is not None and bornes.maxi > bornes.mini:
            lecteur = (
                lecteur.option("partitionColumn", cle)
                .option("lowerBound", str(bornes.mini))
                .option("upperBound", str(bornes.maxi))
                .option("numPartitions", "8")
            )
        return lecteur.load()

    df = spark.read.table(f"{source_open}.{table}")
    # Les noms de colonnes sont insensibles à la casse dans Spark : le filtre est poussé vers SQL Server
    return df.where(F.col(col_maj) > F.to_timestamp(F.lit(depuis))) if depuis else df


def derniere_maj(bronze: str):
    """(dernière DATE_MAJ chargée, borne de relecture = dernière − recouvrement), en texte, ou (None, None)."""
    if complet or not spark.catalog.tableExists(bronze.replace("`", "")):
        return None, None
    r = spark.sql(f"""
        SELECT date_format(max(date_maj), '{FORMAT_TS}') AS derniere,
               date_format(max(date_maj) - make_interval(0, 0, 0, 0, 0, {recouvrement}, 0), '{FORMAT_TS}') AS relecture
        FROM {bronze}
    """).first()
    return r.derniere, r.relecture


spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {JOURNAL} (
        lot_id STRING, table_source STRING, table_bronze STRING, nb_lignes BIGINT,
        depuis TIMESTAMP, jusqua TIMESTAMP, debut TIMESTAMP, fin TIMESTAMP, statut STRING, erreur STRING
    ) COMMENT 'Journal des chargements Open → bronze'
""")

origine = source_open if mode_source == "table" else f"sqlserver:{secret_scope}/{schema_sqlserver}"

# COMMAND ----------

resultats = []
for table_src, table_bronze, col_maj, cle in TABLES:
    bronze = f"`{catalog}`.bronze.{table_bronze}"
    debut = datetime.now()
    derniere, relecture = derniere_maj(bronze)
    try:
        df = lire_source(table_src, col_maj, cle, relecture)
        # Noms de colonnes normalisés (Open est en majuscules)
        df = df.toDF(*[c.lower() for c in df.columns])
        cle_b, maj_b = cle.lower(), col_maj.lower()
        # Une seule version par (clé, DATE_MAJ), et pas celles déjà chargées pendant la fenêtre de recouvrement
        df = df.dropDuplicates([cle_b, maj_b])
        if relecture:
            deja = (
                spark.table(bronze)
                .where(F.col(maj_b) > F.to_timestamp(F.lit(relecture)))
                .select(cle_b, maj_b)
                .distinct()
            )
            df = df.join(deja, [cle_b, maj_b], "left_anti")
        df = (
            df.withColumn("_ingere_le", F.current_timestamp())
            .withColumn("_source", F.lit(f"{mode_source}:{origine}.{table_src}"))
            .withColumn("_lot_id", F.lit(lot_id))
        )
        nb = df.count()
        if nb:
            (
                df.write.mode("overwrite" if complet else "append")
                .option("mergeSchema", "true")
                .option("overwriteSchema", "true" if complet else "false")
                .saveAsTable(bronze)
            )
            spark.sql(f"ALTER TABLE {bronze} SET TBLPROPERTIES ('delta.appendOnly' = '{'false' if complet else 'true'}', "
                      f"'ecmd.couche' = 'bronze', 'ecmd.source' = 'Open.{table_src}', 'ecmd.cle' = '{cle_b}')")
        jusqua = spark.sql(f"SELECT date_format(max(date_maj), '{FORMAT_TS}') m FROM {bronze}").first().m if nb else derniere
        statut, erreur = "OK", None
    except Exception as e:  # on journalise puis on échoue à la fin pour alerter
        nb, jusqua, statut, erreur = 0, derniere, "ERREUR", str(e)[:2000]
    resultats.append((lot_id, table_src, table_bronze, nb, derniere, jusqua, debut, datetime.now(), statut, erreur))
    print(f"{'✔' if statut == 'OK' else '✘'} {table_src:<11} → bronze.{table_bronze:<16} {nb:>6} ligne(s)  "
          f"(dernière maj {derniere or '—'}, relu depuis {relecture or 'le début'})")

(
    spark.createDataFrame(
        resultats,
        "lot_id string, table_source string, table_bronze string, nb_lignes bigint, depuis string, jusqua string, "
        "debut timestamp, fin timestamp, statut string, erreur string",
    )
    .withColumn("depuis", F.to_timestamp("depuis"))
    .withColumn("jusqua", F.to_timestamp("jusqua"))
    .write.mode("append").saveAsTable(JOURNAL)
)

erreurs = [r for r in resultats if r[8] != "OK"]
if erreurs:
    raise RuntimeError("Ingestion en échec : " + "; ".join(f"{r[1]} : {r[9]}" for r in erreurs))
