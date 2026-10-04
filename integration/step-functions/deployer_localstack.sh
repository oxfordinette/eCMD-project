#!/usr/bin/env bash
# Déploie dans LocalStack les deux orchestrations eCMD :
#   - ecmd-invitations-automatiques : 2 Lambdas (lien signé, email SES) ;
#   - ecmd-soumission-certificat    : 2 Lambdas (création du dossier dans Lakebase, accusé de réception SES),
#     à partir du paquet construit par le service « lambda-build » (/opt/ecmd/build/soumission.zip).
# Pas de planification : c'est le job Databricks qui lance la machine à états avec les nouveaux sinistres.
#
# Exécuté automatiquement au démarrage de LocalStack (monté dans /etc/localstack/init/ready.d par
# docker-compose, profil « aws »). Peut aussi être relancé à la main :
#   docker compose exec localstack bash /etc/localstack/init/ready.d/deployer_localstack.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${STEP_FUNCTIONS_SRC:-/opt/ecmd/step-functions}"
[ -d "$SRC/lambdas" ] || SRC="$DIR"
AWS="${AWS_CMD:-awslocal}"
REGION="${AWS_DEFAULT_REGION:-eu-west-3}"
COMPTE="000000000000"
SECRET="${PORTAIL_SECRET_LIENS:?PORTAIL_SECRET_LIENS doit être défini (voir cellmed/.env, 32 caractères minimum)}"
PORTAIL="${PORTAIL_URL:-http://localhost:8081}"
EXPEDITEUR="${SES_EXPEDITEUR:-no-reply@cellmed.fr}"
TMP="$(mktemp -d)"

echo "▶ eCMD Step Functions — région $REGION, portail $PORTAIL"

# ── Expéditeur SES (en AWS réel : domaine vérifié + sortie du « sandbox » SES) ──
$AWS ses verify-email-identity --email-address "$EXPEDITEUR" >/dev/null
echo "  ✔ SES : expéditeur $EXPEDITEUR"

# ── Rôle IAM (LocalStack ne le vérifie pas, AWS si) ──
cat > "$TMP/trust.json" <<JSON
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":["lambda.amazonaws.com","states.amazonaws.com"]},"Action":"sts:AssumeRole"}]}
JSON
$AWS iam create-role --role-name ecmd-orchestration --assume-role-policy-document "file://$TMP/trust.json" >/dev/null 2>&1 || true
ROLE="arn:aws:iam::$COMPTE:role/ecmd-orchestration"

# ── Lambdas ──
( cd "$SRC/lambdas" && python3 -m zipfile -c "$TMP/lambdas.zip" generer_lien.py envoyer_invitation.py )
ENV_LIEN="Variables={PORTAIL_URL=$PORTAIL,PORTAIL_SECRET_LIENS=$SECRET,LIEN_DUREE_JOURS=30}"
ENV_EMAIL="Variables={SES_EXPEDITEUR=$EXPEDITEUR,AWS_ENDPOINT_URL=http://localstack:4566}"
for f in "ecmd-generer-lien:generer_lien.handler:$ENV_LIEN" "ecmd-envoyer-invitation:envoyer_invitation.handler:$ENV_EMAIL"; do
  NOM="${f%%:*}"; RESTE="${f#*:}"; HANDLER="${RESTE%%:*}"; ENV="${RESTE#*:}"
  if $AWS lambda get-function --function-name "$NOM" >/dev/null 2>&1; then
    $AWS lambda update-function-code --function-name "$NOM" --zip-file "fileb://$TMP/lambdas.zip" >/dev/null
    $AWS lambda wait function-updated --function-name "$NOM"
    $AWS lambda update-function-configuration --function-name "$NOM" --environment "$ENV" >/dev/null
  else
    $AWS lambda create-function --function-name "$NOM" --runtime python3.12 --handler "$HANDLER" \
      --zip-file "fileb://$TMP/lambdas.zip" --role "$ROLE" --timeout 30 --environment "$ENV" >/dev/null
  fi
  $AWS lambda wait function-active-v2 --function-name "$NOM"
  echo "  ✔ Lambda $NOM"
done

# ── Machine à états ──
sed -e "s#\${GENERER_LIEN_FUNCTION_ARN}#arn:aws:lambda:$REGION:$COMPTE:function:ecmd-generer-lien#" \
    -e "s#\${ENVOYER_INVITATION_FUNCTION_ARN}#arn:aws:lambda:$REGION:$COMPTE:function:ecmd-envoyer-invitation#" \
    "$SRC/state_machine.asl.json" > "$TMP/sm.json"
SM_ARN="arn:aws:states:$REGION:$COMPTE:stateMachine:ecmd-invitations-automatiques"
if $AWS stepfunctions describe-state-machine --state-machine-arn "$SM_ARN" >/dev/null 2>&1; then
  $AWS stepfunctions update-state-machine --state-machine-arn "$SM_ARN" --definition "file://$TMP/sm.json" >/dev/null
else
  $AWS stepfunctions create-state-machine --name ecmd-invitations-automatiques \
    --definition "file://$TMP/sm.json" --role-arn "$ROLE" >/dev/null
fi
echo "  ✔ Step Functions ecmd-invitations-automatiques"

# ── Soumission du certificat : création du dossier + accusé de réception ──
ZIP_SOUMISSION="${ZIP_SOUMISSION:-/opt/ecmd/build/soumission.zip}"
if [ -f "$ZIP_SOUMISSION" ]; then
  # Variables de connexion à la base (mêmes que le backend), écrites en JSON pour supporter tous les caractères
  python3 - > "$TMP/env_soumission.json" <<'PY'
import json, os
cles = ["DB_MODE", "DB_SCHEMA", "DATABASE_URL", "LAKEBASE_PROJECT", "LAKEBASE_HOST", "LAKEBASE_DATABASE",
        "LAKEBASE_USER", "DATABRICKS_HOST", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET", "SES_EXPEDITEUR"]
env = {k: os.environ[k] for k in cles if os.environ.get(k)}
env.update(SOUMISSION_MODE="step_functions", AWS_ENDPOINT_URL="http://localstack:4566")
print(json.dumps({"Variables": env}))
PY
  for f in "ecmd-creer-dossier:traiter_soumission.creer_dossier" "ecmd-accuse-reception:traiter_soumission.envoyer_accuse"; do
    NOM="${f%%:*}"; HANDLER="${f##*:}"
    if $AWS lambda get-function --function-name "$NOM" >/dev/null 2>&1; then
      $AWS lambda update-function-code --function-name "$NOM" --zip-file "fileb://$ZIP_SOUMISSION" >/dev/null
      $AWS lambda wait function-updated --function-name "$NOM"
      $AWS lambda update-function-configuration --function-name "$NOM" --environment "file://$TMP/env_soumission.json" >/dev/null
    else
      $AWS lambda create-function --function-name "$NOM" --runtime python3.12 --handler "$HANDLER" \
        --zip-file "fileb://$ZIP_SOUMISSION" --role "$ROLE" --timeout 60 --memory-size 512 \
        --environment "file://$TMP/env_soumission.json" >/dev/null
    fi
    $AWS lambda wait function-active-v2 --function-name "$NOM"
    echo "  ✔ Lambda $NOM"
  done
  sed -e "s#\${CREER_DOSSIER_FUNCTION_ARN}#arn:aws:lambda:$REGION:$COMPTE:function:ecmd-creer-dossier#" \
      -e "s#\${ENVOYER_ACCUSE_FUNCTION_ARN}#arn:aws:lambda:$REGION:$COMPTE:function:ecmd-accuse-reception#" \
      "$SRC/soumission.asl.json" > "$TMP/soumission.json"
  SM2="arn:aws:states:$REGION:$COMPTE:stateMachine:ecmd-soumission-certificat"
  if $AWS stepfunctions describe-state-machine --state-machine-arn "$SM2" >/dev/null 2>&1; then
    $AWS stepfunctions update-state-machine --state-machine-arn "$SM2" --definition "file://$TMP/soumission.json" >/dev/null
  else
    $AWS stepfunctions create-state-machine --name ecmd-soumission-certificat \
      --definition "file://$TMP/soumission.json" --role-arn "$ROLE" >/dev/null
  fi
  echo "  ✔ Step Functions ecmd-soumission-certificat"
else
  echo "  ⚠ $ZIP_SOUMISSION absent : soumission non déployée (le service lambda-build a-t-il tourné ?)"
fi

# Ancienne planification EventBridge (version précédente) : supprimée si présente
$AWS events remove-targets --rule ecmd-invitations-planification --ids sm >/dev/null 2>&1 || true
$AWS events delete-rule --name ecmd-invitations-planification >/dev/null 2>&1 || true

rm -rf "$TMP"
echo "✔ Déployé. Test : bash /opt/ecmd/step-functions/tester_localstack.sh"
