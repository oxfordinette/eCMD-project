-- ═══════════════════════════════════════════════════════════════════════════
-- SILVER · SINISTRE (arrêts de travail déclarés dans Open, SCD type 1)
-- Les codes Open sont traduits en libellés eCMD.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TEMPORARY VIEW sinistre_valide (
  CONSTRAINT id_present       EXPECT (id_sinistre IS NOT NULL)      ON VIOLATION DROP ROW,
  CONSTRAINT numero_present   EXPECT (numero_sinistre IS NOT NULL)  ON VIOLATION DROP ROW,
  CONSTRAINT assure_present   EXPECT (id_assure IS NOT NULL)        ON VIOLATION DROP ROW,
  CONSTRAINT date_maj_presente EXPECT (date_maj IS NOT NULL)        ON VIOLATION DROP ROW,
  -- Avertissements
  CONSTRAINT debut_arret_present EXPECT (date_debut_arret IS NOT NULL),
  CONSTRAINT nature_connue    EXPECT (type_arret IS NOT NULL),
  CONSTRAINT dates_coherentes EXPECT (date_declaration IS NULL OR date_debut_arret IS NULL OR date_declaration >= date_debut_arret - INTERVAL 30 DAYS)
)
AS SELECT
  CAST(id_sinistre AS BIGINT)                    AS id_sinistre,
  upper(trim(num_sinistre))                      AS numero_sinistre,
  CAST(id_assure AS BIGINT)                      AS id_assure,
  CAST(id_contrat AS BIGINT)                     AS id_contrat,
  CAST(date_declaration AS DATE)                 AS date_declaration,
  CAST(date_debut_arret AS DATE)                 AS date_debut_arret,
  upper(trim(code_nature))                       AS nature_code,
  CASE upper(trim(code_nature))
    WHEN 'MAL' THEN 'Maladie non professionnelle'
    WHEN 'AT'  THEN 'Accident de travail'
    WHEN 'MP'  THEN 'Maladie professionnelle'
    WHEN 'MAT' THEN 'État de grossesse'
  END                                            AS type_arret,
  CASE upper(trim(statut)) WHEN 'O' THEN 'OUVERT' WHEN 'C' THEN 'CLOS' WHEN 'A' THEN 'ANNULE' ELSE upper(trim(statut)) END AS statut,
  CAST(date_maj AS TIMESTAMP)                    AS date_maj,
  _ingere_le
FROM STREAM(${catalog}.bronze.open_sinistre);

CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.sinistre
COMMENT 'Sinistres / arrêts de travail Open, dernière version connue'
TBLPROPERTIES ('ecmd.couche' = 'silver');

CREATE FLOW sinistre_scd1 AS AUTO CDC INTO ${catalog}.silver.sinistre
FROM STREAM(sinistre_valide)
KEYS (id_sinistre)
SEQUENCE BY date_maj
STORED AS SCD TYPE 1;
