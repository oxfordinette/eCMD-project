# Certificat médical — portail assuré (eCMD)

Deuxième application du projet eCMD : le portail où l'**assuré** remplit son attestation d'arrêt de travail.
À la transmission, sa déclaration devient automatiquement un **dossier CellMed « À valider »** (mêmes données,
documents compris).

- **Frontend** : React + TypeScript (Vite), d'après les maquettes du portail.
- **Backend** : le backend partagé `../cellmed/backend` (routes `/api/portail/*`).
- **Données** : la même base Lakebase (schéma `cellmed`, tables `invitation` et `declaration_assure`).

## Parcours

1. Un nouveau sinistre Open est envoyé par Databricks à **AWS Step Functions**, qui génère un **lien signé** et
   envoie l'email d'invitation (SES) — voir `../integration/step-functions/README.md`. Aucun opérateur n'intervient.
2. L'assuré ouvre son lien personnel `/acces/<jeton>`. À la première ouverture, le backend vérifie la signature et
   crée l'invitation à partir du sinistre Open (`ecmd_gold.sinistre_prerempli`, préremplissage du certificat) :
   - **01 Langue**
   - **02 Vérification d'identité** : date de naissance (5 essais maximum, puis blocage)
   - **03 Code de vérification** : choix SMS ou email (coordonnées masquées)
   - **04 Vérification du code** : code à 6 chiffres, valable 10 minutes (5 essais maximum)
3. Le formulaire en 7 rubriques est enregistré automatiquement (brouillon) :
   Administratif · Arrêt de travail · Antécédents & état · Soins & traitements · Évolution & reprise ·
   Documents justificatifs · Récapitulatif.
4. Les **pièces justificatives exigées dépendent des réponses** (accident du travail, traitements,
   spécialistes, hospitalisation, invalidité, incapacité permanente, retraite).
5. À la transmission, la déclaration est figée puis confiée à **AWS Step Functions**
   (`SOUMISSION_MODE=step_functions`), qui crée le dossier CellMed dans Lakebase et envoie un accusé de réception
   avec sa référence. C'est **seulement à ce moment** que les opérateurs voient le sinistre. En développement
   (`SOUMISSION_MODE=direct`), le backend crée le dossier immédiatement. Le dossier contient : identité, contrat, arrêt, pathologie (référentiel CellMed),
   traitements, historique, documents. La déclaration complète apparaît dans la fiche dossier.

Les règles (pièces exigées, validation, récapitulatif, correspondance vers le dossier) sont centralisées dans
`cellmed/backend/app/portail_logic.py`.

## Lancer

Avec Docker, depuis `cellmed/` (lance aussi CellMed et le backend) :

```bash
cd ../cellmed
docker compose up --build
```

- CellMed : http://localhost:8080
- Certificat médical : http://localhost:8081/acces/demo-marie-dupont (invitation de démonstration,
  date de naissance **12/04/1985**)

En développement :

```bash
npm install
npm run dev        # http://localhost:5174, /api est redirigé vers le backend (port 8000)
```

## Codes de vérification et notifications

- `NOTIF_MODE=dev` (par défaut) : rien n'est envoyé. Les emails et SMS sont écrits dans les logs du backend,
  et le code est affiché sur l'écran de saisie (bandeau « Mode démonstration »).
- `NOTIF_MODE=aws` : emails via **Amazon SES**, SMS via **Amazon SNS**. Pour tester avec **LocalStack** :

  ```bash
  # dans cellmed/.env
  NOTIF_MODE=aws
  AWS_ENDPOINT_URL=http://localstack:4566
  AWS_ACCESS_KEY_ID=test
  AWS_SECRET_ACCESS_KEY=test
  ```

  puis `docker compose --profile aws up --build`. Au démarrage, le backend déclare l'expéditeur SES
  (`SES_EXPEDITEUR`) auprès de LocalStack. Les messages envoyés sont visibles via l'API de LocalStack
  (`http://localhost:4566/_aws/ses` et `/_aws/sns/sms-messages`).

## Sécurité

- Le lien d'invitation est signé (HMAC-SHA256, secret partagé avec la Lambda, expiration 30 jours) ; il ne
  contient que le n° de sinistre. Lien falsifié → 404, expiré → 410. Aucune donnée personnelle n'est renvoyée
  avant la vérification de la date de naissance.
- Codes à usage unique stockés hachés, expirant, avec limitation des essais et du renvoi (30 s).
- Jeton de session (2 h) stocké haché ; supprimé à la transmission.

## Reste à faire

- **Assuré bloqué** (5 dates de naissance erronées) : les opérateurs ne voyant plus les invitations, prévoir un
  déblocage (délai automatique, ou procédure du support).
- Traduction anglaise (le choix de langue est enregistré, l'interface est en français).
- Envoi réel en production (identités SES vérifiées, sortie du bac à sable SES, Sender ID SMS).
- Notification de l'assuré lors des demandes de pièces complémentaires faites dans CellMed.
