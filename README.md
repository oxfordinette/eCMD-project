# eCMD — Certificat Médical Dématérialisé

| Composant | Dossier | Rôle |
|---|---|---|
| **CellMed** | `cellmed/` | Portail des opérateurs : traitement des dossiers CMD (créés à la soumission du certificat), référentiels. Contient aussi le **backend partagé** (FastAPI) et le `docker-compose.yml`. |
| **Certificat médical** | `certificat-medical/` | Portail de l'assuré : vérification d'identité (date de naissance + code), attestation en 7 rubriques. La déclaration crée un dossier CellMed. |
| **Données** | `data/` | Databricks Asset Bundle : architecture médaillon (bronze / silver / gold) alimentée par le backoffice **Open** (SQL Server), synchronisée vers Lakebase pour préremplir le certificat. |
| **Intégration AWS** | `integration/step-functions/` | Step Functions + Lambdas : lien signé et email d'invitation (SES) pour chaque nouveau sinistre envoyé par Databricks. |

```
Open ──► Databricks (bronze → silver → gold) ──► gold.nouveau_sinistre ──► AWS Step Functions ──► email (SES)
                         │                                              (lien signé)            │
                         └─► Lakebase (sinistre_prerempli) ◄── backend eCMD ◄── portail Certificat médical (assuré)
                                                                   │
                                     dossier créé à la soumission ─┴──► CellMed (opérateurs)
```

Démarrage local : voir `cellmed/README.md` (`docker compose up --build` dans `cellmed/`).
