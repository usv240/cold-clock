param([string]$ProjectId="agentic-fleet-2026",[string]$Location="us-central1")
$ErrorActionPreference="Stop";$Job="cold-clock-wake-scan";$Service="cold-clock";$Identity="agent-wake-scheduler@$ProjectId.iam.gserviceaccount.com"
$Url=gcloud run services describe $Service --project $ProjectId --region $Location --format="value(status.url)"
$Existing=gcloud scheduler jobs list --project $ProjectId --location $Location --filter="name:$Job" --format="value(name)"
if($Existing){gcloud scheduler jobs update http $Job --project $ProjectId --location $Location --schedule="* * * * *" --time-zone=Etc/UTC --uri="$Url/internal/wakes/scan" --http-method=POST --oidc-service-account-email=$Identity --oidc-token-audience=$Url --attempt-deadline=30s --max-retry-attempts=3 --min-backoff=5s --max-backoff=60s --max-doublings=2 --quiet}
else{gcloud scheduler jobs create http $Job --project $ProjectId --location $Location --schedule="* * * * *" --time-zone=Etc/UTC --uri="$Url/internal/wakes/scan" --http-method=POST --oidc-service-account-email=$Identity --oidc-token-audience=$Url --attempt-deadline=30s --max-retry-attempts=3 --min-backoff=5s --max-backoff=60s --max-doublings=2 --quiet}
gcloud scheduler jobs run $Job --project $ProjectId --location $Location
