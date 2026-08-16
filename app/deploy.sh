#!/usr/bin/env bash
set -euo pipefail

: "${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

gcloud run deploy cold-clock \
  --source . \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,USE_FIRESTORE=true,ENABLE_CLOUD_TRACE=true" \
  --quiet

SERVICE_URL="$(gcloud run services describe cold-clock --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --format='value(status.url)')"
SCHEDULER_IDENTITY="agent-wake-scheduler@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com"
gcloud run services update cold-clock --project "$GOOGLE_CLOUD_PROJECT" --region "$REGION" --update-env-vars "SCHEDULER_AUDIENCE=$SERVICE_URL,SCHEDULER_SERVICE_ACCOUNT=$SCHEDULER_IDENTITY" --quiet

