# Orchestrations AWS Step Functions

Deux machines à états :

| Machine à états | Déclenchée par | Rôle |
|---|---|---|
| `ecmd-invitations-automatiques` | le job Databricks | Lien signé + email d'invitation pour chaque nouveau sinistre |
| `ecmd-soumission-certificat` | le backend, à la soumission du certificat | Création du dossier CellMed dans Lakebase + accusé de réception |

## 1. Invitations automatiques

Quand un nouveau sinistre arrive dans Open, le job Databricks le fait passer par bronze → silver → gold, met à jour
la copie Lakebase, puis **envoie lui-même** les nouveaux sinistres (`gold.nouveau_sinistre`) à Step Functions.
AWS génère un **lien signé** et envoie l'**email d'invitation** (SES). Le backend n'intervient qu'au moment où
l'assuré clique sur son lien.

```
Job Databricks (fin)                         AWS Step Functions « ecmd-invitations-automatiques »
  gold.nouveau_sinistre ── StartExecution ──►  Map (10 en parallèle), pour chaque sinistre :
  {sinistres: [{numero_sinistre, prenom,         ├─ GenererLien     Lambda ecmd-generer-lien      → lien signé
               nom, email, type_certificat}]}    └─ EnvoyerEmail    Lambda ecmd-envoyer-invitation → email SES
                                                    (erreur passagère : 4 réessais ; échec : consigné)
  passage suivant : DescribeExecution ◄──────  Bilan : {resultats: [{numero_sinistre, statut: envoye | echec}]}
  → gold.sinistre_envoye (envoye / echec, échec retenté jusqu'à 3 fois)

Assuré : clic sur le lien ──► portail Certificat médical ──► backend : vérifie la signature,
                                                            crée l'invitation à partir de sinistre_prerempli
```

**Règle métier** : rien n'est écrit dans la base de l'application avant que l'assuré ouvre son lien, et CellMed ne
voit le sinistre qu'une fois le certificat soumis (création du dossier).

| Fichier | Rôle |
|---|---|
| `state_machine.asl.json` | Définition Step Functions (ARN des Lambdas en variables `${…}`) |
| `lambdas/generer_lien.py` | Lien `…/acces/<n° sinistre>.<expiration>.<signature>` (HMAC-SHA256, 30 jours) |
| `lambdas/envoyer_invitation.py` | Email d'invitation (texte + HTML) via SES ; l'adresse n'est jamais écrite en entier dans les journaux |
| `deployer_localstack.sh` | Déploie expéditeur SES + Lambdas + machine à états dans LocalStack |
| `tester_localstack.sh` | Lance une exécution de test et affiche l'email reçu |
| `aws/` | Rôle IAM utilisé par Databricks (production) |
| `soumission.asl.json` | Machine à états de la soumission (voir section 2) |
| `lambdas/traiter_soumission.py` | Lambdas `ecmd-creer-dossier` et `ecmd-accuse-reception` |
| `construire_lambdas.py` | Construit `soumission.zip` (code partagé du backend + dépendances), service compose `lambda-build` |

### Le lien signé

```
https://<portail>/acces/SIN-2026-00001.tnx81f.nLZxbjuhws0JaQPTFXTa4Q
                        └ n° sinistre ─┘└ exp ┘└──── signature ────┘
```

- Signature : HMAC-SHA256 avec `PORTAIL_SECRET_LIENS`, secret partagé **uniquement** entre la Lambda et le backend
  (en production : AWS Secrets Manager, variable `SECRET_LIENS_ARN` de la Lambda). Sans le secret, impossible de
  fabriquer un lien. Le lien ne contient aucune donnée personnelle.
- Le backend (`cellmed/backend/app/liens.py`, même algorithme) refuse un lien falsifié (404), expiré (410) ou dont
  le sinistre est clos. Plusieurs liens pour un même sinistre mènent à la même invitation.
- L'accès reste protégé ensuite par la date de naissance puis le code à usage unique.
- Générer un secret : `openssl rand -hex 32`.

### Données transmises par Databricks

Uniquement `numero_sinistre`, `prenom`, `nom`, `email`, `type_certificat` : ce qu'il faut pour écrire l'email.
Le NSS, la date de naissance et l'adresse ne quittent pas Databricks / Lakebase. L'entrée d'une exécution reste
visible dans l'historique Step Functions (90 jours) : restreindre l'accès à la console à l'équipe d'exploitation.

## 2. Soumission du certificat

```
Portail ──► backend : validation du formulaire, déclaration figée (invitation « soumise »)
                 └─► StartExecution ecmd-soumission-certificat  {invitation_id}      (nom : soumission-<id>)
                        ├─ TraitementsComplementaires  (emplacement réservé : contrôles, OCR, appel à Open…)
                        ├─ CreerDossier       Lambda ecmd-creer-dossier   → tables cellmed de Lakebase
                        │                     (dossier, documents, historique, déclaration ; 4 réessais)
                        └─ EnvoyerAccuseReception  Lambda ecmd-accuse-reception → email SES avec la référence
CellMed lit le dossier dans Lakebase comme avant.
```

- **Aucune donnée de santé dans Step Functions** : seule l'`invitation_id` circule. La Lambda relit la déclaration
  dans Lakebase ; l'historique des exécutions ne contient donc ni pathologie ni traitement.
- **Même règle que le backend** : la Lambda embarque `cellmed/backend/app/soumission.py` (avec config, db, models,
  portail_logic), copié par `construire_lambdas.py`. Une modification de la règle se fait à un seul endroit.
- **Idempotent** : relancer l'exécution ou la Lambda ne crée pas de second dossier.
- **Échec** : l'invitation reste « soumise » sans dossier ; corriger la cause puis relancer l'exécution (Redrive).
- **Assuré** : la page de confirmation annonce un email avec la référence du dossier (créé quelques secondes plus tard).
- Activation : `SOUMISSION_MODE=step_functions` dans `cellmed/.env` (`direct` = création immédiate par le backend).
- Accès à la base : les Lambdas utilisent les mêmes variables que le backend (`DB_MODE`, `LAKEBASE_*`,
  `DATABRICKS_CLIENT_ID/SECRET`, `DATABASE_URL`) ; en production, les ranger dans Secrets Manager.

## Avec LocalStack (local)

Dans `cellmed/.env` :

```
PORTAIL_SECRET_LIENS=<openssl rand -hex 32>
NOTIF_MODE=aws
AWS_ENDPOINT_URL=http://localstack:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

```bash
cd cellmed
docker compose --profile aws up --build
docker compose exec localstack bash /opt/ecmd/step-functions/tester_localstack.sh SIN-2026-00001
```

Au démarrage, le service `lambda-build` construit d'abord `soumission.zip` (téléchargement des dépendances Python,
une minute environ), puis LocalStack déploie les deux machines à états. Pour tester la soumission, mettre aussi
`SOUMISSION_MODE=step_functions` dans `cellmed/.env`.

Le test simule l'envoi de Databricks pour un sinistre de la table de démonstration (`DB_MODE=postgres`) et affiche
l'email reçu. Le lien s'ouvre dans le portail (http://localhost:8081) : date de naissance de Marie Dupont = 12/04/1985.

Databricks (dans le cloud) ne peut pas joindre LocalStack sur ton ordinateur : le job Databricks reste en
`mode_declenchement: journal` (il affiche ce qu'il enverrait). Pour un test de bout en bout, exposer LocalStack par
un tunnel et renseigner `aws_endpoint_url` dans la cible `dev` du bundle.

## En production (AWS)

1. **Secret** : Secrets Manager `ecmd/portail-secret-liens` (même valeur que `PORTAIL_SECRET_LIENS` du backend).
2. **Lambdas** Python 3.12 :
   - `ecmd-generer-lien` : `PORTAIL_URL`, `SECRET_LIENS_ARN`, `LIEN_DUREE_JOURS` ; droit
     `secretsmanager:GetSecretValue` sur ce secret ;
   - `ecmd-envoyer-invitation` : `SES_EXPEDITEUR` ; droit `ses:SendEmail` limité à l'identité d'envoi.
3. **SES** : vérifier le domaine d'envoi (SPF, DKIM, DMARC) et demander la sortie du *sandbox* SES (sinon seules
   les adresses vérifiées reçoivent les emails).
4. **Machine à états** `ecmd-invitations-automatiques` (rôle : `lambda:InvokeFunction` sur les deux Lambdas).
5. **Accès de Databricks** : voir `aws/README.md` (rôle IAM + service credential Unity Catalog).
