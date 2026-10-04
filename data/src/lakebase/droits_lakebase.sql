-- À exécuter dans l'éditeur SQL du projet Lakebase (base databricks_postgres), avec le compte propriétaire,
-- APRÈS la création de la table synchronisée ecmd_gold.sinistre_prerempli.
-- Donne au service principal du backend eCMD le droit de lire les données Open synchronisées.
-- Remplacer <client-id> par l'Application ID du service principal (ex. 6c8d22be-…).

GRANT USAGE ON SCHEMA ecmd_gold TO "<client-id>";
GRANT SELECT ON ALL TABLES IN SCHEMA ecmd_gold TO "<client-id>";

-- Vérification
SELECT count(*) AS sinistres, count(*) FILTER (WHERE motif_non_eligible IS NULL) AS eligibles
FROM ecmd_gold.sinistre_prerempli;
