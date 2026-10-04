-- ═══════════════════════════════════════════════════════════════════════════
-- SILVER · ENTREPRISE et CONTRAT (référentiels, SCD type 1 : dernière valeur connue)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TEMPORARY VIEW entreprise_valide (
  CONSTRAINT id_present EXPECT (id_entreprise IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT date_maj_presente EXPECT (date_maj IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT siren_valide EXPECT (siren RLIKE '^[0-9]{9}$')
)
AS SELECT
  CAST(id_entreprise AS BIGINT)                 AS id_entreprise,
  trim(raison_sociale)                          AS raison_sociale_open,
  -- Libellé lisible : « ACME GROUPE » → « Acme Groupe »
  initcap(lower(trim(raison_sociale)))          AS raison_sociale,
  regexp_replace(siren, '[^0-9]', '')           AS siren,
  CAST(date_maj AS TIMESTAMP)                   AS date_maj,
  _ingere_le
FROM STREAM(${catalog}.bronze.open_entreprise);

CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.entreprise
COMMENT 'Entreprises clientes (Open), dernière version connue'
TBLPROPERTIES ('ecmd.couche' = 'silver');

CREATE FLOW entreprise_scd1 AS AUTO CDC INTO ${catalog}.silver.entreprise
FROM STREAM(entreprise_valide)
KEYS (id_entreprise)
SEQUENCE BY date_maj
STORED AS SCD TYPE 1;


CREATE TEMPORARY VIEW contrat_valide (
  CONSTRAINT id_present EXPECT (id_contrat IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT numero_present EXPECT (numero_contrat IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT date_maj_presente EXPECT (date_maj IS NOT NULL) ON VIOLATION DROP ROW
)
AS SELECT
  CAST(id_contrat AS BIGINT)                    AS id_contrat,
  upper(trim(num_contrat))                      AS numero_contrat,
  CAST(id_entreprise AS BIGINT)                 AS id_entreprise,
  -- « AXA FRANCE » → « Axa France » ; les sigles courants restent en capitales
  CASE upper(trim(assureur)) WHEN 'AXA' THEN 'AXA' WHEN 'AXA FRANCE' THEN 'AXA France' ELSE initcap(lower(trim(assureur))) END AS assureur,
  upper(trim(`partition`))                      AS `partition`,
  CASE upper(trim(college))
    WHEN 'CADRE' THEN 'Cadre'
    WHEN 'NON CADRE' THEN 'Non-cadre'
    WHEN 'NON-CADRE' THEN 'Non-cadre'
    WHEN 'AGENT DE MAITRISE' THEN 'Agent de maîtrise'
    ELSE initcap(lower(trim(college)))
  END                                           AS college,
  CAST(date_effet AS DATE)                      AS date_effet,
  CAST(date_resiliation AS DATE)                AS date_resiliation,
  CAST(date_maj AS TIMESTAMP)                   AS date_maj,
  _ingere_le
FROM STREAM(${catalog}.bronze.open_contrat);

CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.contrat
COMMENT 'Contrats prévoyance (Open), dernière version connue'
TBLPROPERTIES ('ecmd.couche' = 'silver');

CREATE FLOW contrat_scd1 AS AUTO CDC INTO ${catalog}.silver.contrat
FROM STREAM(contrat_valide)
KEYS (id_contrat)
SEQUENCE BY date_maj
STORED AS SCD TYPE 1;
