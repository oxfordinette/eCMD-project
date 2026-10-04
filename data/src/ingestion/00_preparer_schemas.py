# Databricks notebook source
# MAGIC %md
# MAGIC # Préparation des schémas eCMD
# MAGIC Crée (si besoin) les schémas de l'architecture médaillon dans le catalogue eCMD :
# MAGIC `bronze` (copie brute d'Open), `silver` (nettoyé, historisé), `gold` (prêt à l'usage), `open_sim` (simulateur).

# COMMAND ----------

dbutils.widgets.text("catalog", "ecmd_dev")
catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

try:
    spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
except Exception as e:  # droits insuffisants : le catalogue doit être créé par un administrateur
    print(f"Catalogue {catalog} non créé ({e.__class__.__name__}) — on suppose qu'il existe déjà.")

COMMENTAIRES = {
    "bronze": "Copie brute et historisée des tables du backoffice Open (append only)",
    "silver": "Données Open nettoyées, contrôlées (expectations) et historisées (SCD2)",
    "gold": "Données métier prêtes à l'usage : sinistres préremplis pour le Certificat médical",
    "open_sim": "Simulateur de la base Open (environnements de dev uniquement)",
}
for schema, commentaire in COMMENTAIRES.items():
    # Apostrophes échappées (« l'usage ») pour ne pas fermer la chaîne SQL
    texte = commentaire.replace("\\", "\\\\").replace("'", "\\'")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}` COMMENT '{texte}'")
    print(f"✔ {catalog}.{schema}")
