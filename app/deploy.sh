#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

gcloud run deploy cold-clock \
  --source . \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1 \
  --concurrency 10 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,USE_FIRESTORE=true,ENABLE_CLOUD_TRACE=true,ALLOW_GLOBAL_RESET=false,ALLOW_DEIDENTIFIED_PILOT=false,ENABLE_LIVE_MODELS=true" \
  --update-secrets "API_KEY_PEPPER=developer-api-pepper:1" \
  --quiet

# A Cloud Run service answers at two URLs: the deterministic project-number form and the hashed
# form that `describe` reports. Cloud Scheduler mints its OIDC token for one of them, so the app
# accepts every form, plus whatever audience the existing scheduler job is configured with.
SERVICE_URL="$(gcloud run services describe cold-clock --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --format='value(status.url)')"
PROJECT_NUMBER="$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format='value(projectNumber)')"
DETERMINISTIC_URL="https://cold-clock-${PROJECT_NUMBER}.${REGION}.run.app"
JOB_AUDIENCE="$(gcloud scheduler jobs describe cold-clock-wake-scan --project "$GOOGLE_CLOUD_PROJECT" --location "$REGION" --format='value(httpTarget.oidcToken.audience)' 2>/dev/null || true)"
AUDIENCES="$(printf '%s\n' "$SERVICE_URL" "$DETERMINISTIC_URL" "$JOB_AUDIENCE" | sed 's#/$##' | awk 'NF && !seen[$0]++' | paste -sd, -)"
SCHEDULER_IDENTITY="agent-wake-scheduler@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com"
gcloud run services update cold-clock --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --update-env-vars "^|^SCHEDULER_AUDIENCE=$AUDIENCES|SCHEDULER_SERVICE_ACCOUNT=$SCHEDULER_IDENTITY" --quiet

# Traffic may have been pinned to a named revision by an earlier canary; a deploy must actually serve.
gcloud run services update-traffic cold-clock --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --to-latest --quiet
