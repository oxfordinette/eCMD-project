/* ════════════════════════════════════════════════════════════════════════════
   Open (SQL Server) — compte de lecture pour Databricks (eCMD)
   À exécuter par un DBA d'Open. Remplacer <base_open> et le mot de passe.
   Le mot de passe est ensuite stocké dans le secret scope Databricks `ecmd-open`
   (voir data/README.md), jamais dans le code.
   ════════════════════════════════════════════════════════════════════════════ */

USE [master];
CREATE LOGIN [ecmd_lecture] WITH PASSWORD = N'<mot-de-passe-long-et-aleatoire>',
    CHECK_POLICY = ON, DEFAULT_DATABASE = [<base_open>];
GO

USE [<base_open>];
CREATE USER [ecmd_lecture] FOR LOGIN [ecmd_lecture] WITH DEFAULT_SCHEMA = [dbo];

-- Lecture seule, limitée aux 4 tables utilisées par eCMD (moindre privilège)
GRANT SELECT ON dbo.ENTREPRISE TO [ecmd_lecture];
GRANT SELECT ON dbo.CONTRAT    TO [ecmd_lecture];
GRANT SELECT ON dbo.ASSURE     TO [ecmd_lecture];
GRANT SELECT ON dbo.SINISTRE   TO [ecmd_lecture];
-- Nécessaire à Lakehouse Federation pour lister les tables et colonnes
GRANT VIEW DEFINITION ON SCHEMA::dbo TO [ecmd_lecture];
GO

/* ── Recommandé : lectures sans bloquer l'application Open ──────────────────
   Avec READ_COMMITTED_SNAPSHOT, les lectures d'eCMD lisent la dernière version
   validée sans poser de verrous partagés (pas besoin de NOLOCK, qui peut lire
   des données non validées ou en double). À valider avec l'équipe Open :
   nécessite un accès exclusif bref à la base au moment de l'activation.        */
-- ALTER DATABASE [<base_open>] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;

/* ── Réseau ─────────────────────────────────────────────────────────────────
   Le calcul Databricks (serverless, région us-east-2) doit joindre le port 1433 :
   - SQL Server dans AWS : PrivateLink / VPC peering via une Network Connectivity
     Configuration (NCC) Databricks ;
   - SQL Server sur site ou autre cloud : VPN / Direct Connect, ou ouverture du
     pare-feu aux IP de sortie stables de la NCC.
   Le chiffrement TLS est exigé (encrypt=true) : le certificat du serveur doit être
   valide, sinon trust_server_certificate=true (à éviter en production).        */

-- Vérification avec le compte ecmd_lecture
SELECT 'ASSURE' AS table_open, COUNT(*) AS lignes, MAX(DATE_MAJ) AS derniere_maj FROM dbo.ASSURE
UNION ALL SELECT 'SINISTRE', COUNT(*), MAX(DATE_MAJ) FROM dbo.SINISTRE
UNION ALL SELECT 'CONTRAT', COUNT(*), MAX(DATE_MAJ) FROM dbo.CONTRAT
UNION ALL SELECT 'ENTREPRISE', COUNT(*), MAX(DATE_MAJ) FROM dbo.ENTREPRISE;
