# CellMed — portail opérateurs (eCMD)

> Ce dossier contient aussi le **backend partagé** et le `docker-compose.yml` de tout eCMD :
> CellMed (port 8080) et le portail assuré **Certificat médical** (`../certificat-medical`, port 8081).

Premier composant du projet eCMD : le portail utilisé par les opérateurs CellMed pour traiter les dossiers CMD (Certificat Médical Dématérialisé).

- **Frontend** : React + TypeScript (Vite), styles repris du mockup `cellmed-mockup.html`
- **Backend** : FastAPI + SQLAlchemy
- **Données** : Postgres **Lakebase** dans Databricks (schéma `cellmed`), ou Postgres local pour le dev
- **Exécution** : Docker Compose en local

## Périmètre

> **Règle métier** : un opérateur CellMed n'a connaissance d'un sinistre qu'une fois le certificat médical
> **soumis** par l'assuré (création du dossier). Les invitations sont entièrement automatiques
> (Databricks → AWS Step Functions → email SES) et n'apparaissent pas dans CellMed.

Toutes les vues du mockup sont développées :

| Vue | Contenu |
|---|---|
| Tableau de bord | Cartes par statut, derniers dossiers traités |
| Listes par statut | Recherche, filtres urgence / type / sous-statut pièces |
| Fiche dossier | Parcours, identité, contrat, arrêt, médical, analyse du gestionnaire, historique, commentaires, actions (valider, pièces + relance, avis médical, expertise), dépôt de documents avec aperçu réel (PDF, images) et téléchargement |
| Recherche avancée | 12 critères combinables |
| Statistiques | 5 indicateurs, répartition par statut et urgence, pathologies les plus fréquentes |
| Pathologies | Groupes, liste filtrable, fiche, ajout / modification, documents types (dépôt, suppression) |
| Utilisateurs | Liste filtrable, ajout / modification / suppression, rôles et statut |
| Paramètres | Profil, préférences de notification (enregistrés en base) |
| Déclaration de l'assuré | Dans la fiche dossier : déclaration complète saisie sur le portail Certificat médical |

Restent à brancher : le **SSO** (connexion, mot de passe, droits par rôle — l'utilisateur courant est pour l'instant défini dans `.env`) et l'**envoi réel des notifications** (e-mail / SMS à l'assuré, préférences de notification).

Les documents des données de démonstration n'ont pas de fichier : leur aperçu est simulé. Les documents déposés depuis le portail sont stockés (Lakebase par défaut, ou Volume Unity Catalog avec `STORAGE_MODE=volume`).

## Démarrage rapide

### Option A : avec Lakebase (Databricks)

Le projet Lakebase est renseigné dans `.env.example` (`LAKEBASE_PROJECT` accepte l'uid visible dans l'URL de l'interface, l'id technique ou le nom affiché). Le backend trouve la branche par défaut et son endpoint lecture/écriture.

**Authentification** : les API Lakebase exigent OAuth (un token personnel PAT est refusé).

- **Docker** : utiliser un service principal.
  1. Settings → Identity and access → Service principals → créer `cellmed-backend`, puis générer un secret OAuth.
  2. Dans l'éditeur SQL du projet Lakebase (base `databricks_postgres`), avec le compte propriétaire :
     ```sql
     CREATE EXTENSION IF NOT EXISTS databricks_auth;
     SELECT databricks_create_role('<client-id>', 'SERVICE_PRINCIPAL');
     GRANT CONNECT, CREATE ON DATABASE databricks_postgres TO "<client-id>";
     ```
  3. Dans `cellmed/.env` : `DATABRICKS_CLIENT_ID` et `DATABRICKS_CLIENT_SECRET` (et pas de `DATABRICKS_CONFIG_PROFILE`).
- **Sans Docker (dev)** : réutiliser la session Databricks CLI avec `DATABRICKS_CONFIG_PROFILE=<profil>` dans `backend/.env`.

Vérifier puis lancer :
```bash
cd cellmed
cp .env.example .env
docker compose build
docker compose run --rm backend python -m app.lakebase_check
docker compose up
```
Ouvrir http://localhost:8080.

Au premier démarrage, le backend crée le schéma `cellmed` et les tables, puis charge les données de démonstration du mockup si la base est vide (`SEED_ON_STARTUP=true`). Le mot de passe Postgres est un token OAuth Lakebase renouvelé automatiquement avant expiration (`backend/app/db.py`).

### Option B : Postgres local (sans Databricks)

```bash
cd cellmed
cp .env.example .env
# mettre DB_MODE=postgres
docker compose --profile local-db up --build
```

### Développement sans Docker

```bash
# Backend
cd cellmed/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # adapter DB_MODE / DATABASE_URL
uvicorn app.main:app --reload --port 8000

# Frontend (autre terminal)
cd cellmed/frontend
npm install
npm run dev               # http://localhost:5173, /api est proxifié vers :8000
```

Documentation interactive de l'API : http://localhost:8000/docs

## Structure

```
cellmed/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py            # application FastAPI
│   │   ├── config.py          # variables d'environnement
│   │   ├── db.py              # connexion Postgres / Lakebase (token OAuth)
│   │   ├── models.py          # tables : dossier, document, evenement, commentaire, piece_requise,
│   │   │                      #          pathologie, pathologie_document, medecin_conseil,
│   │   │                      #          utilisateur, fichier
│   │   ├── schemas.py         # schémas Pydantic
│   │   ├── auth.py            # utilisateur courant (provisoire, en attendant le SSO)
│   │   ├── storage.py         # contenu des fichiers : Lakebase ou Volume Unity Catalog
│   │   ├── lakebase_check.py  # vérification de la connexion Lakebase
│   │   ├── notifications.py   # emails / SMS : mode dev ou AWS SES + SNS (LocalStack)
│   │   ├── portail_logic.py   # règles du formulaire assuré (pièces, validation, récapitulatif)
│   │   ├── seed.py            # chargement des données de démo
│   │   ├── seed_data.json     # données extraites du mockup
│   │   └── routers/
│   │       ├── dossiers.py    # listes, recherche, détail, actions, commentaires, documents
│   │       ├── pathologies.py # référentiel et documents types
│   │       ├── utilisateurs.py# utilisateurs et profil
│   │       ├── statistiques.py
│   │       ├── fichiers.py    # affichage / téléchargement
│   │       ├── portail.py     # portail assuré : lien signé, accès par code, formulaire, soumission
│   │       └── referentiels.py
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── pages/             # Accueil, ListeDossiers, DossierDetail, Recherche, Statistiques,
    │   │                      # Pathologies, PathologieDetail, Utilisateurs, Parametres
    │   ├── components/        # Layout, DossierTable, DocViewer, Commentaires, Timeline, ActionModals,
    │   │                      # UploadZone, ConfirmModal, PathologieModal
    │   ├── api.ts, types.ts, statuts.tsx, format.ts
    │   └── styles.css         # CSS du mockup
    ├── nginx.conf
    └── Dockerfile
```

## API principale

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/dossiers/compteurs` | Nombre de dossiers par statut |
| GET | `/api/dossiers?status=&q=&urgence=&type=&pieces_statut=&tri=` | Liste filtrée |
| GET | `/api/dossiers/{id}` | Détail complet |
| POST | `/api/dossiers/{id}/actions` | `validate`, `pieces`, `expertise`, `avis` |
| PUT | `/api/dossiers/{id}/analyse` | Analyse du gestionnaire |
| POST | `/api/dossiers/{id}/commentaires` | Ajouter un commentaire |
| POST | `/api/dossiers/{id}/pieces/{piece_id}/relance` | Relancer une pièce manquante |
| POST | `/api/dossiers/{id}/documents` | Déposer un document (multipart) |
| GET | `/api/fichiers/{document\|pathologie-document}/{id}` | Afficher / télécharger un fichier |
| GET | `/api/referentiels` | Décisions, médecins conseil, délais, groupes, catégories |
| GET | `/api/statistiques` | Indicateurs |
| GET/POST/PUT | `/api/pathologies[/{code}]` | Référentiel des pathologies |
| GET | `/api/pathologies/groupes` | Groupes et nombre de pathologies |
| POST/DELETE | `/api/pathologies/{code}/documents[/{id}]` | Documents types |
| GET/POST/PUT/DELETE | `/api/utilisateurs[/{id}]` | Gestion des utilisateurs |
| … | `/api/portail/{jeton}/…` | Portail assuré (voir `../certificat-medical/README.md`) ; accepte les liens signés envoyés par AWS |
| GET/PUT | `/api/profil` | Profil de l'utilisateur courant |
| PATCH | `/api/profil/preferences` | Préférences de notification |

## Workflow des dossiers

```
valider ──► pieces ──► expertise ──► avis-medical ──► clotures
   └──────────┴────────────┴──────────────┴──► (validation = clôture)
```

Chaque action ajoute une entrée à l'historique et l'étape au parcours du dossier. Un dossier clôturé n'accepte plus d'action.

## Prochaines étapes suggérées

1. **SSO** de l'entreprise et droits par rôle (admin, manager, médecin, gestionnaire).
2. **Notifications** réelles : e-mail / SMS à l'assuré (pièces, relances), préférences des gestionnaires.
3. Réception des **pièces complémentaires** envoyées par l'assuré (passage « Pièces reçues »).
4. Migrations de schéma (**Alembic**) à la place du `create_all`.
5. **Ingestion** des dossiers depuis les autres composants eCMD.
