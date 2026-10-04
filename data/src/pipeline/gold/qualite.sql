-- ═══════════════════════════════════════════════════════════════════════════
-- GOLD · QUALITÉ DES DONNÉES OPEN
-- Indicateurs pour piloter la qualité de la source (à exposer dans un dashboard
-- Databricks SQL ou une alerte).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.qualite_open
COMMENT 'Indicateurs de qualité des données Open (volumétrie, rejets, complétude)'
TBLPROPERTIES ('ecmd.couche' = 'gold')
AS
WITH a AS (SELECT * FROM ${catalog}.silver.assure WHERE __END_AT IS NULL),
     s AS (SELECT * FROM ${catalog}.gold.sinistre_prerempli)
SELECT 'Assurés (version courante)' AS indicateur, CAST(count(*) AS DOUBLE) AS valeur, 'nombre' AS unite FROM a
UNION ALL SELECT 'Assurés en quarantaine', count(DISTINCT coalesce(CAST(id_assure AS STRING), nss)), 'nombre' FROM ${catalog}.silver.assure_quarantaine
UNION ALL SELECT 'Assurés sans email', round(100 * avg(CASE WHEN email IS NULL THEN 1 ELSE 0 END), 1), '%' FROM a
UNION ALL SELECT 'Assurés sans téléphone mobile', round(100 * avg(CASE WHEN telephone IS NULL THEN 1 ELSE 0 END), 1), '%' FROM a
UNION ALL SELECT 'Assurés injoignables (ni email ni téléphone)', round(100 * avg(CASE WHEN email IS NULL AND telephone IS NULL THEN 1 ELSE 0 END), 1), '%' FROM a
UNION ALL SELECT 'Versions historisées (SCD2)', count(*), 'nombre' FROM ${catalog}.silver.assure
UNION ALL SELECT 'Sinistres ouverts', count_if(statut_sinistre = 'OUVERT'), 'nombre' FROM s
UNION ALL SELECT 'Sinistres prêts pour invitation', count_if(motif_non_eligible IS NULL), 'nombre' FROM s
UNION ALL SELECT 'Sinistres ouverts non éligibles', count_if(statut_sinistre = 'OUVERT' AND motif_non_eligible IS NOT NULL), 'nombre' FROM s;
