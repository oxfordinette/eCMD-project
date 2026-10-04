-- ════════════════════════════════════════════════════════════════════════════
-- Lakehouse Federation : catalogue Unity Catalog pointant sur la base SQL Server d'Open
-- ────────────────────────────────────────────────────────────────────────────
-- À exécuter UNE FOIS dans l'éditeur SQL Databricks, par un administrateur du metastore
-- (droit CREATE CONNECTION et CREATE CATALOG).
--
-- Prérequis :
--   1. Compte de lecture créé dans Open        → data/open/acces_lecture_ecmd.sql
--   2. Secrets dans le scope `ecmd-open`        → voir data/README.md (host, port, database, user, password)
--   3. Réseau : le calcul serverless joint SQL Server sur le port 1433 (NCC / PrivateLink / pare-feu)
-- ════════════════════════════════════════════════════════════════════════════

CREATE CONNECTION IF NOT EXISTS open_sqlserver TYPE sqlserver
OPTIONS (
  host     '<hote-sql-server-open>',     -- ex. open-sql.mondomaine.local ou xxx.rds.amazonaws.com
  port     '1433',
  user     secret('ecmd-open', 'user'),
  password secret('ecmd-open', 'password'),
  trustServerCertificate 'false'
)
COMMENT 'Base SQL Server du backoffice Open (lecture seule, compte ecmd_lecture)';

-- Remplacer OPEN par le nom réel de la base Open
CREATE FOREIGN CATALOG IF NOT EXISTS open_fed
USING CONNECTION open_sqlserver
OPTIONS (database 'OPEN')
COMMENT 'Backoffice Open (SQL Server) en lecture via Lakehouse Federation';

-- Accès : seul le job d'ingestion (et les data engineers) lit Open directement.
-- Remplacer par le groupe / service principal qui exécute le job.
GRANT USE CATALOG ON CATALOG open_fed TO `ecmd-data-engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA open_fed.dbo TO `ecmd-data-engineers`;

-- Vérification rapide (le notebook src/federation/verifier_open.py fait un contrôle complet)
SHOW TABLES IN open_fed.dbo;
SELECT count(*) AS assures, max(DATE_MAJ) AS derniere_maj FROM open_fed.dbo.ASSURE;
