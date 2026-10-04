#!/usr/bin/env bash
# Simule l'envoi de Databricks : lance la machine à états avec un sinistre de démonstration,
# affiche le résultat puis l'email reçu par SES (LocalStack conserve les emails envoyés).
#   docker compose exec localstack bash /opt/ecmd/step-functions/tester_localstack.sh [SIN-2026-00001] [email]
set -euo pipefail
REGION="${AWS_DEFAULT_REGION:-eu-west-3}"
SM_ARN="arn:aws:states:$REGION:000000000000:stateMachine:ecmd-invitations-automatiques"
NUM="${1:-SIN-2026-00001}"; EMAIL="${2:-marie.dupont@entreprise.fr}"
ENTREE=$(printf '{"origine":"test","run_id":"test","sinistres":[{"numero_sinistre":"%s","prenom":"Marie","nom":"DUPONT","email":"%s","type_certificat":"Initial"}]}' "$NUM" "$EMAIL")
ARN=$(awslocal stepfunctions start-execution --state-machine-arn "$SM_ARN" --input "$ENTREE" --query executionArn --output text)
for _ in $(seq 1 30); do
  ETAT=$(awslocal stepfunctions describe-execution --execution-arn "$ARN" --query status --output text)
  [ "$ETAT" != "RUNNING" ] && break; sleep 2
done
echo "Exécution : $ETAT"
awslocal stepfunctions describe-execution --execution-arn "$ARN" --query output --output text
echo "── Dernier email SES ──"
curl -s "http://localhost:4566/_aws/ses?email=$(awslocal ses list-identities --query 'Identities[0]' --output text)" \
  | python3 -c "import json,sys; m=json.load(sys.stdin)['messages'][-1]; print('À :', m['Destination']['ToAddresses']); print(m['Body']['text_part'])"
