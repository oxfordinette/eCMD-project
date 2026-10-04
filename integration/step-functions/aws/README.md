# Accès de Databricks à Step Functions (production)

Le job Databricks lance la machine à états avec un **service credential** Unity Catalog : aucune clé AWS n'est
stockée, Databricks obtient des accès temporaires en endossant un rôle IAM. Ce rôle ne peut **que** lancer
`ecmd-invitations-automatiques` et lire le résultat de ses exécutions.

## 1. Créer le rôle IAM (AWS)

1. IAM → Roles → **Create role** → *Custom trust policy* : coller `confiance.json` en laissant
   `<external-id-du-service-credential>` à `0000` pour l'instant ; remplacer `<compte-aws>`.
2. Nom : `ecmd-databricks-declencheur`.
3. Ajouter la politique en ligne `permissions.json` (remplacer `<compte-aws>`, et la région si ce n'est pas eu-west-3).

## 2. Créer le service credential (Databricks)

1. Catalog → **External data** → **Credentials** → **Create credential** → type **Service credential**, AWS IAM role.
2. Nom : `ecmd-aws-stepfunctions` ; ARN du rôle : `arn:aws:iam::<compte-aws>:role/ecmd-databricks-declencheur`.
3. Databricks affiche un **External ID** : le recopier dans la politique de confiance du rôle (étape 1.1), à la place
   de `0000`.
4. Donner l'usage au compte qui exécute le job (toi en dev, un service principal en prod) :
   ```sql
   GRANT ACCESS ON SERVICE CREDENTIAL `ecmd-aws-stepfunctions` TO `<utilisateur ou service principal>`;
   ```

## 3. Renseigner le bundle

Dans `data/databricks.yml`, cible `prod` (ou `dev` pour essayer avec un vrai compte AWS) :

```yaml
mode_declenchement: aws
state_machine_arn: arn:aws:states:eu-west-3:<compte-aws>:stateMachine:ecmd-invitations-automatiques
pipeline_synchro_lakebase: <id du pipeline de la table synchronisée>
```

Puis `databricks bundle deploy -t prod`. La tâche `declencher_invitations` du job affiche le nombre de sinistres
transmis ; le détail est dans `gold.sinistre_envoye`.
