# Databricks notebook source
# MAGIC %md
# MAGIC # Vérification de la source Open (SQL Server)
# MAGIC
# MAGIC Compare la base Open réelle au **contrat de lecture** d'eCMD (`data/open/schema_open_sqlserver.sql`) :
# MAGIC 1. connexion et présence des 4 tables ;
# MAGIC 2. colonnes attendues et types compatibles ;
# MAGIC 3. qualité des colonnes clés : `DATE_MAJ` renseignée, unicité de `NUM_SINISTRE`, codes connus
# MAGIC    (`CODE_NATURE`, `STATUT`, `SEXE`).
# MAGIC
# MAGIC À lancer avant d'activer le job d'ingestion : `databricks bundle run ecmd_open_verification -t prod`.
# MAGIC Les écarts **bloquants** font échouer le notebook ; les **avertissements** sont seulement affichés.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql import types as T

dbutils.widgets.text("source_open", "ecmd_dev.open_sim")
dbutils.widgets.dropdown("mode_source", "table", ["table", "jdbc"])
dbutils.widgets.text("secret_scope", "ecmd-open")
dbutils.widgets.text("schema_sqlserver", "dbo")

source_open = dbutils.widgets.get("source_open")
mode_source = dbutils.widgets.get("mode_source")
secret_scope = dbutils.widgets.get("secret_scope")
schema_sqlserver = dbutils.widgets.get("schema_sqlserver")

# Contrat de lecture : colonne → famille de type attendue
ENTIER, TEXTE, DATE, HORODATAGE = "entier", "texte", "date", "horodatage"
CONTRAT = {
    "ENTREPRISE": {"ID_ENTREPRISE": ENTIER, "RAISON_SOCIALE": TEXTE, "SIREN": TEXTE, "DATE_MAJ": HORODATAGE},
    "CONTRAT": {"ID_CONTRAT": ENTIER, "NUM_CONTRAT": TEXTE, "ID_ENTREPRISE": ENTIER, "ASSUREUR": TEXTE,
                "PARTITION": TEXTE, "COLLEGE": TEXTE, "DATE_EFFET": DATE, "DATE_RESILIATION": DATE,
                "DATE_MAJ": HORODATAGE},
    "ASSURE": {"ID_ASSURE": ENTIER, "NUM_SS": TEXTE, "NOM": TEXTE, "PRENOM": TEXTE, "DATE_NAISSANCE": DATE,
               "SEXE": TEXTE, "EMAIL": TEXTE, "TEL_MOBILE": TEXTE, "ADRESSE_1": TEXTE, "CODE_POSTAL": TEXTE,
               "VILLE": TEXTE, "PROFESSION": TEXTE, "ID_CONTRAT": ENTIER, "DATE_MAJ": HORODATAGE},
    "SINISTRE": {"ID_SINISTRE": ENTIER, "NUM_SINISTRE": TEXTE, "ID_ASSURE": ENTIER, "ID_CONTRAT": ENTIER,
                 "DATE_DECLARATION": DATE, "DATE_DEBUT_ARRET": DATE, "CODE_NATURE": TEXTE, "STATUT": TEXTE,
                 "DATE_MAJ": HORODATAGE},
}
CODES = {
    ("SINISTRE", "CODE_NATURE"): ["MAL", "AT", "MP", "MAT"],
    ("SINISTRE", "STATUT"): ["O", "C", "A"],
    ("ASSURE", "SEXE"): ["1", "2"],
}


def famille(t: T.DataType) -> str:
    if isinstance(t, (T.ByteType, T.ShortType, T.IntegerType, T.LongType)) or (
        isinstance(t, T.DecimalType) and t.scale == 0
    ):
        return ENTIER
    if isinstance(t, (T.StringType, T.VarcharType, T.CharType)):
        return TEXTE
    if isinstance(t, T.DateType):
        return DATE
    if isinstance(t, (T.TimestampType, T.TimestampNTZType)):
        return HORODATAGE
    return t.simpleString()


def _secret(cle: str, defaut: str | None = None) -> str:
    try:
        return dbutils.secrets.get(secret_scope, cle)
    except Exception:
        if defaut is None:
            raise
        return defaut


def lire(table: str):
    if mode_source == "jdbc":
        url = (f"jdbc:sqlserver://{_secret('host')}:{_secret('port', '1433')};databaseName={_secret('database')};"
               f"encrypt=true;trustServerCertificate={_secret('trust_server_certificate', 'false')};"
               "loginTimeout=30;applicationName=ecmd-verification")
        return (spark.read.format("jdbc").option("url", url).option("user", _secret("user"))
                .option("password", _secret("password"))
                .option("driver", "com.microsoft.sqlserver.jdbc.SQLServerDriver")
                .option("dbtable", f"[{schema_sqlserver}].[{table}]").load())
    return spark.read.table(f"{source_open}.{table}")


# COMMAND ----------

constats = []  # (niveau, table, objet, constat)


def noter(niveau, table, objet, constat):
    constats.append((niveau, table, objet, constat))


for table, colonnes in CONTRAT.items():
    try:
        df = lire(table)
        reel = {f.name.upper(): f.dataType for f in df.schema.fields}
    except Exception as e:
        noter("BLOQUANT", table, "table", f"illisible : {str(e).splitlines()[0][:300]}")
        continue

    for col, attendu in colonnes.items():
        if col not in reel:
            noter("BLOQUANT", table, col, "colonne absente")
        elif famille(reel[col]) != attendu:
            noter("AVERTISSEMENT", table, col, f"type {reel[col].simpleString()} (attendu : {attendu})")
    for col in sorted(set(reel) - set(colonnes)):
        noter("INFO", table, col, "colonne non utilisée par eCMD")

    if "DATE_MAJ" not in reel:
        continue
    stats = df.agg(
        F.count(F.lit(1)).alias("lignes"),
        F.sum(F.col("DATE_MAJ").isNull().cast("int")).alias("maj_nulles"),
        F.max("DATE_MAJ").alias("derniere_maj"),
    ).first()
    noter("INFO", table, "volume", f"{stats.lignes} ligne(s), dernière DATE_MAJ : {stats.derniere_maj}")
    if stats.maj_nulles:
        noter("BLOQUANT", table, "DATE_MAJ", f"{stats.maj_nulles} ligne(s) sans DATE_MAJ : jamais ingérées")

    if table == "SINISTRE" and "NUM_SINISTRE" in reel:
        doublons = df.groupBy("NUM_SINISTRE").count().where("count > 1").count()
        if doublons:
            noter("BLOQUANT", table, "NUM_SINISTRE", f"{doublons} numéro(s) en double : clé de la table gold")

    for (t, col), valeurs in CODES.items():
        if t == table and col in reel:
            inconnus = [r[0] for r in df.select(F.upper(F.trim(F.col(col)))).distinct().collect()
                        if r[0] is not None and r[0] not in valeurs]
            if inconnus:
                noter("AVERTISSEMENT", table, col, f"codes non traduits : {', '.join(sorted(inconnus)[:20])}")

# COMMAND ----------

ordre = {"BLOQUANT": 0, "AVERTISSEMENT": 1, "INFO": 2}
rapport = spark.createDataFrame(
    sorted(constats, key=lambda c: (ordre[c[0]], c[1], c[2])) or [("INFO", "-", "-", "aucun constat")],
    "niveau string, table_open string, objet string, constat string",
)
display(rapport)

bloquants = [c for c in constats if c[0] == "BLOQUANT"]
print(f"{len(bloquants)} bloquant(s), {sum(c[0] == 'AVERTISSEMENT' for c in constats)} avertissement(s).")
if bloquants:
    raise RuntimeError("Source Open non conforme au contrat eCMD :\n" +
                       "\n".join(f"- {t}.{o} : {c}" for _, t, o, c in bloquants))
