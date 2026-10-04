/* ════════════════════════════════════════════════════════════════════════════
   Open (backoffice) — schéma SQL Server SUPPOSÉ par eCMD
   ────────────────────────────────────────────────────────────────────────────
   Ce script décrit le « contrat » de lecture d'eCMD : les tables et colonnes que
   l'ingestion Databricks lit dans Open. Il sert :
     - de référence pour comparer avec le vrai schéma d'Open (voir le notebook
       src/federation/verifier_open.py qui fait la comparaison automatiquement) ;
     - à créer une base Open de test (SQL Server 2019+ / Azure SQL).
   Si les vrais noms diffèrent, deux options :
     a) créer dans Open des VUES portant ces noms (recommandé, rien à changer côté eCMD) ;
     b) adapter les vues *_standardise / *_valide de la couche silver.
   ════════════════════════════════════════════════════════════════════════════ */

CREATE TABLE dbo.ENTREPRISE (
    ID_ENTREPRISE      INT            NOT NULL PRIMARY KEY,
    RAISON_SOCIALE     NVARCHAR(200)  NOT NULL,
    SIREN              CHAR(9)        NULL,
    DATE_MAJ           DATETIME2(3)   NOT NULL CONSTRAINT DF_ENTREPRISE_MAJ DEFAULT SYSDATETIME()
);

CREATE TABLE dbo.CONTRAT (
    ID_CONTRAT         INT            NOT NULL PRIMARY KEY,
    NUM_CONTRAT        VARCHAR(30)    NOT NULL,
    ID_ENTREPRISE      INT            NOT NULL REFERENCES dbo.ENTREPRISE (ID_ENTREPRISE),
    ASSUREUR           NVARCHAR(100)  NULL,
    [PARTITION]        VARCHAR(30)    NULL,       -- mot réservé en T-SQL : toujours entre crochets
    COLLEGE            NVARCHAR(50)   NULL,       -- CADRE / NON CADRE / AGENT DE MAITRISE
    DATE_EFFET         DATE           NULL,
    DATE_RESILIATION   DATE           NULL,
    DATE_MAJ           DATETIME2(3)   NOT NULL CONSTRAINT DF_CONTRAT_MAJ DEFAULT SYSDATETIME()
);

CREATE TABLE dbo.ASSURE (
    ID_ASSURE          INT            NOT NULL PRIMARY KEY,
    NUM_SS             VARCHAR(21)    NULL,       -- NSS, éventuellement saisi avec espaces
    NOM                NVARCHAR(100)  NULL,
    PRENOM             NVARCHAR(100)  NULL,
    DATE_NAISSANCE     DATE           NULL,
    SEXE               CHAR(1)        NULL,       -- 1 = homme, 2 = femme
    EMAIL              NVARCHAR(254)  NULL,
    TEL_MOBILE         VARCHAR(30)    NULL,       -- formats libres : 06 12 34 56 78, +33…, 0033…
    ADRESSE_1          NVARCHAR(200)  NULL,
    CODE_POSTAL        VARCHAR(10)    NULL,
    VILLE              NVARCHAR(100)  NULL,
    PROFESSION         NVARCHAR(150)  NULL,
    ID_CONTRAT         INT            NULL REFERENCES dbo.CONTRAT (ID_CONTRAT),
    DATE_MAJ           DATETIME2(3)   NOT NULL CONSTRAINT DF_ASSURE_MAJ DEFAULT SYSDATETIME()
);

CREATE TABLE dbo.SINISTRE (
    ID_SINISTRE        INT            NOT NULL PRIMARY KEY,
    NUM_SINISTRE       VARCHAR(30)    NOT NULL UNIQUE,   -- ex. SIN-2026-00001
    ID_ASSURE          INT            NOT NULL REFERENCES dbo.ASSURE (ID_ASSURE),
    ID_CONTRAT         INT            NULL REFERENCES dbo.CONTRAT (ID_CONTRAT),
    DATE_DECLARATION   DATE           NULL,
    DATE_DEBUT_ARRET   DATE           NULL,
    CODE_NATURE        VARCHAR(5)     NULL,       -- MAL / AT / MP / MAT
    STATUT             CHAR(1)        NOT NULL,   -- O = ouvert, C = clos, A = annulé
    DATE_MAJ           DATETIME2(3)   NOT NULL CONSTRAINT DF_SINISTRE_MAJ DEFAULT SYSDATETIME()
);
GO

/* ── Indispensable à l'ingestion incrémentale ───────────────────────────────
   Chaque passage (toutes les 15 min) lit « WHERE DATE_MAJ > @dernier_chargement ».
   Sans index, c'est un parcours complet de la table à chaque fois.              */
CREATE INDEX IX_ENTREPRISE_DATE_MAJ ON dbo.ENTREPRISE (DATE_MAJ);
CREATE INDEX IX_CONTRAT_DATE_MAJ    ON dbo.CONTRAT    (DATE_MAJ);
CREATE INDEX IX_ASSURE_DATE_MAJ     ON dbo.ASSURE     (DATE_MAJ);
CREATE INDEX IX_SINISTRE_DATE_MAJ   ON dbo.SINISTRE   (DATE_MAJ);
GO

/* ── DATE_MAJ doit être mise à jour à CHAQUE modification ───────────────────
   Si l'application Open ne le fait pas elle-même, un déclencheur le garantit
   (exemple pour ASSURE, à décliner sur les trois autres tables).               */
CREATE OR ALTER TRIGGER dbo.TR_ASSURE_DATE_MAJ ON dbo.ASSURE AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF UPDATE(DATE_MAJ) RETURN;     -- déjà renseignée par l'application
    UPDATE a SET DATE_MAJ = SYSDATETIME()
    FROM dbo.ASSURE a JOIN inserted i ON i.ID_ASSURE = a.ID_ASSURE;
END;
GO
