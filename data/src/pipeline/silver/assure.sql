-- ═══════════════════════════════════════════════════════════════════════════
-- SILVER · ASSURÉ
-- Source : bronze.open_assure (copie brute d'Open.ASSURE, ajout seul)
-- Cible  : silver.assure — historisée (SCD type 2) : une ligne par version d'assuré,
--          version courante = __END_AT IS NULL
-- Rejets : silver.assure_quarantaine (lignes non conformes, avec le motif)
-- ═══════════════════════════════════════════════════════════════════════════

-- Standardisation des champs (formats hétérogènes dans Open)
CREATE TEMPORARY VIEW assure_standardise AS
SELECT
  CAST(id_assure AS BIGINT)                                   AS id_assure,
  -- NSS : 13 caractères (+ 2 de clé), Corse 2A/2B acceptée
  upper(regexp_replace(num_ss, '[^0-9ABab]', ''))             AS nss,
  upper(trim(nom))                                            AS nom,
  initcap(lower(trim(prenom)))                                AS prenom,
  CAST(date_naissance AS DATE)                                AS date_naissance,
  CASE trim(sexe) WHEN '1' THEN 'M' WHEN '2' THEN 'F' END     AS sexe,
  CASE WHEN lower(trim(email)) RLIKE '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$' THEN lower(trim(email)) END AS email,
  -- Téléphone au format international E.164 (+33…)
  CASE
    WHEN regexp_replace(tel_mobile, '[^0-9+]', '') RLIKE '^\\+[0-9]{8,15}$' THEN regexp_replace(tel_mobile, '[^0-9+]', '')
    WHEN regexp_replace(tel_mobile, '[^0-9]', '') RLIKE '^00[0-9]{8,15}$'   THEN concat('+', substr(regexp_replace(tel_mobile, '[^0-9]', ''), 3))
    WHEN regexp_replace(tel_mobile, '[^0-9]', '') RLIKE '^0[1-9][0-9]{8}$'  THEN concat('+33', substr(regexp_replace(tel_mobile, '[^0-9]', ''), 2))
  END                                                         AS telephone,
  trim(adresse_1)                                             AS adresse_ligne,
  trim(code_postal)                                           AS code_postal,
  initcap(lower(trim(ville)))                                 AS ville,
  trim(profession)                                            AS profession,
  CAST(id_contrat AS BIGINT)                                  AS id_contrat,
  CAST(date_maj AS TIMESTAMP)                                 AS date_maj,
  _ingere_le,
  _source
FROM STREAM(${catalog}.bronze.open_assure);

-- Contrôle de la clé du NSS (97 - numéro mod 97), Corse : 2A → 19, 2B → 18
CREATE TEMPORARY VIEW assure_controle AS
SELECT
  *,
  CASE
    WHEN nss IS NULL OR nss NOT RLIKE '^[12][0-9]{4}([0-9]{2}|2A|2B)[0-9]{6}([0-9]{2})?$' THEN false
    WHEN length(nss) = 13 THEN true
    ELSE 97 - pmod(CAST(replace(replace(substr(nss, 1, 13), '2A', '19'), '2B', '18') AS DECIMAL(13, 0)), 97)
         = CAST(substr(nss, 14, 2) AS INT)
  END AS nss_valide
FROM STREAM(assure_standardise);

-- Lignes conformes (les autres sont écartées ici et conservées en quarantaine)
CREATE TEMPORARY VIEW assure_valide (
  CONSTRAINT id_present        EXPECT (id_assure IS NOT NULL)        ON VIOLATION DROP ROW,
  CONSTRAINT nss_correct       EXPECT (nss_valide)                   ON VIOLATION DROP ROW,
  CONSTRAINT identite_complete EXPECT (nom IS NOT NULL AND prenom IS NOT NULL AND date_naissance IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT naissance_plausible EXPECT (date_naissance BETWEEN DATE'1900-01-01' AND current_date()) ON VIOLATION DROP ROW,
  CONSTRAINT date_maj_presente EXPECT (date_maj IS NOT NULL)         ON VIOLATION DROP ROW,
  -- Avertissements (la ligne est gardée, l'écart est mesuré dans les métriques du pipeline)
  CONSTRAINT joignable         EXPECT (email IS NOT NULL OR telephone IS NOT NULL)
)
-- Les expectations portent sur les colonnes produites par la vue : nss_valide est donc gardée ici
-- et retirée au moment d'écrire silver.assure (COLUMNS * EXCEPT ci-dessous).
AS SELECT * FROM STREAM(assure_controle);

CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.assure
COMMENT 'Assurés Open nettoyés et historisés (SCD2). Version courante : __END_AT IS NULL'
TBLPROPERTIES ('ecmd.couche' = 'silver', 'ecmd.contient_donnees_sante' = 'false', 'ecmd.donnees_personnelles' = 'true');

CREATE FLOW assure_scd2 AS AUTO CDC INTO ${catalog}.silver.assure
FROM STREAM(assure_valide)
KEYS (id_assure)
SEQUENCE BY date_maj
COLUMNS * EXCEPT (nss_valide)
STORED AS SCD TYPE 2
TRACK HISTORY ON * EXCEPT (date_maj, _ingere_le, _source);

-- Quarantaine : lignes rejetées avec le motif, pour correction dans Open
CREATE OR REFRESH STREAMING TABLE ${catalog}.silver.assure_quarantaine
COMMENT 'Assurés Open rejetés par les contrôles qualité (à corriger dans Open)'
TBLPROPERTIES ('ecmd.couche' = 'silver')
AS SELECT
  id_assure, nss, nom, prenom, date_naissance, date_maj, _ingere_le, _source,
  concat_ws(' ; ',
    CASE WHEN id_assure IS NULL THEN 'Identifiant manquant' END,
    CASE WHEN NOT nss_valide THEN 'NSS invalide' END,
    CASE WHEN nom IS NULL OR prenom IS NULL OR date_naissance IS NULL THEN 'Identité incomplète' END,
    CASE WHEN date_naissance NOT BETWEEN DATE'1900-01-01' AND current_date() THEN 'Date de naissance non plausible' END,
    CASE WHEN date_maj IS NULL THEN 'DATE_MAJ manquante' END
  ) AS motif
FROM STREAM(assure_controle)
WHERE id_assure IS NULL OR NOT nss_valide OR nom IS NULL OR prenom IS NULL OR date_naissance IS NULL
   OR date_naissance NOT BETWEEN DATE'1900-01-01' AND current_date() OR date_maj IS NULL;
