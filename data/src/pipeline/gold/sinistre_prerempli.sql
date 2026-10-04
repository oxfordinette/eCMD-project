-- ═══════════════════════════════════════════════════════════════════════════
-- GOLD · SINISTRE PRÉREMPLI
-- Une ligne par sinistre Open, avec tout ce qu'il faut pour préremplir le
-- certificat médical : assuré (version courante), contrat, entreprise.
--
-- C'est le CONTRAT D'INTERFACE avec l'application eCMD :
--   · synchronisée vers Lakebase (table synchronisée, clé primaire numero_sinistre)
--   · lue par le backend quand l'assuré ouvre son lien (création de l'invitation, préremplissage du certificat)
--   · source de gold.nouveau_sinistre, envoyée à AWS Step Functions par le job (invitations automatiques)
-- Toute évolution des colonnes doit être répercutée dans le backend (app/open_data.py).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.gold.sinistre_prerempli (
  CONSTRAINT numero_unique EXPECT (numero_sinistre IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Sinistres Open préremplis pour le portail Certificat médical (synchronisé vers Lakebase)'
TBLPROPERTIES (
  'ecmd.couche' = 'gold',
  'ecmd.cle_primaire' = 'numero_sinistre'
  -- Synchronisation Lakebase en mode « Snapshot » : le Change Data Feed (modes Triggered / Continuous)
  -- n'est pas disponible sur une vue matérialisée.
)
AS
WITH assure_courant AS (
  SELECT * FROM ${catalog}.silver.assure WHERE __END_AT IS NULL
),
sinistre_ordonne AS (
  SELECT
    s.*,
    -- Arrêt précédent du même assuré (pour distinguer certificat initial / de suivi)
    lag(s.date_debut_arret) OVER (PARTITION BY s.id_assure ORDER BY s.date_debut_arret, s.id_sinistre) AS debut_arret_precedent
  FROM ${catalog}.silver.sinistre s
),
assemble AS (
  SELECT
    s.numero_sinistre,
    s.id_sinistre                                   AS id_sinistre_open,
    s.statut                                        AS statut_sinistre,
    s.nature_code,
    s.type_arret,
    s.date_declaration,
    s.date_debut_arret,
    CASE WHEN s.debut_arret_precedent >= s.date_debut_arret - INTERVAL 180 DAYS THEN 'Suivi' ELSE 'Initial' END AS type_certificat,
    -- Assuré
    a.id_assure                                     AS id_assure_open,
    a.nss,
    a.nom,
    a.prenom,
    a.date_naissance,
    a.email,
    a.telephone,
    concat_ws(', ', a.adresse_ligne, concat_ws(' ', a.code_postal, a.ville)) AS adresse,
    a.profession,
    -- Contrat & entreprise (le contrat du sinistre prime sur celui de l'assuré)
    c.numero_contrat,
    c.assureur,
    c.`partition`,
    c.college,
    e.raison_sociale                                AS entreprise,
    e.siren,
    greatest(s.date_maj, a.date_maj, c.date_maj, e.date_maj) AS date_maj_open
  FROM sinistre_ordonne s
  LEFT JOIN assure_courant a ON a.id_assure = s.id_assure
  LEFT JOIN ${catalog}.silver.contrat c ON c.id_contrat = coalesce(s.id_contrat, a.id_contrat)
  LEFT JOIN ${catalog}.silver.entreprise e ON e.id_entreprise = c.id_entreprise
)
SELECT
  *,
  CASE
    WHEN statut_sinistre <> 'OUVERT' THEN 'Sinistre clos ou annulé'
    WHEN id_assure_open IS NULL THEN 'Assuré introuvable ou en quarantaine (voir silver.assure_quarantaine)'
    WHEN email IS NULL THEN 'Aucun email valide dans Open (invitation envoyée par email uniquement)'
    WHEN date_debut_arret IS NULL THEN 'Date de début de l’arrêt manquante'
    WHEN date_debut_arret < date_sub(current_date(), ${fenetre_invitation_jours}) THEN 'Arrêt trop ancien'
    WHEN numero_contrat IS NULL THEN 'Contrat introuvable'
  END                                               AS motif_non_eligible,
  current_timestamp()                               AS calcule_le
FROM assemble;

-- Les sinistres à envoyer à AWS Step Functions sont dans la vue gold.nouveau_sinistre, créée par la tâche
-- « declencher_invitations » du job (src/invitations/) : éligibles ET pas encore transmis (gold.sinistre_envoye).
