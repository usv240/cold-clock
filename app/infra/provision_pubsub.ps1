param([string]$ProjectId="agentic-fleet-2026",[string]$Location="us-central1")
# gcloud writes progress to stderr; check exit codes rather than letting PowerShell abort on stderr text.
$ErrorActionPreference="Continue";$Service="cold-clock";$Identity="agent-wake-scheduler@$ProjectId.iam.gserviceaccount.com"
function Invoke-Gcloud([string[]]$GcloudArgs){ $out = & gcloud @GcloudArgs 2>&1; if($LASTEXITCODE -ne 0){ throw "gcloud $($GcloudArgs[0..1] -join ' ') failed: $out" }; return ($out | Where-Object { $_ -is [string] }) }
$ProjectNumber=(Invoke-Gcloud @("projects","describe",$ProjectId,"--format=value(projectNumber)")) | Select-Object -First 1
$Audience="https://$Service-$ProjectNumber.$Location.run.app"
$PubSubAgent="service-$ProjectNumber@gcp-sa-pubsub.iam.gserviceaccount.com"
# Pub/Sub must be allowed to mint OIDC tokens for the worker identity (idempotent).
Invoke-Gcloud @("iam","service-accounts","add-iam-policy-binding",$Identity,"--project",$ProjectId,"--member=serviceAccount:$PubSubAgent","--role=roles/iam.serviceAccountTokenCreator","--quiet") | Out-Null
foreach($pair in @(@("cold-clock-sensor-events","/internal/events/sensor"),@("cold-clock-utility-events","/internal/events/utility"))){
  $Topic=$pair[0];$Path=$pair[1];$Sub="$Topic-push"
  $topicExists = Invoke-Gcloud @("pubsub","topics","list","--project",$ProjectId,"--filter=name:$Topic","--format=value(name)")
  if(-not $topicExists){ Invoke-Gcloud @("pubsub","topics","create",$Topic,"--project",$ProjectId,"--quiet") | Out-Null }
  $subExists = Invoke-Gcloud @("pubsub","subscriptions","list","--project",$ProjectId,"--filter=name:$Sub","--format=value(name)")
  if($subExists){ Invoke-Gcloud @("pubsub","subscriptions","modify-push-config",$Sub,"--project",$ProjectId,"--push-endpoint=$Audience$Path","--push-auth-service-account=$Identity","--push-auth-token-audience=$Audience","--quiet") | Out-Null }
  else{ Invoke-Gcloud @("pubsub","subscriptions","create",$Sub,"--project",$ProjectId,"--topic=$Topic","--push-endpoint=$Audience$Path","--push-auth-service-account=$Identity","--push-auth-token-audience=$Audience","--ack-deadline=30","--min-retry-delay=5s","--max-retry-delay=60s","--quiet") | Out-Null }
  "$Topic -> $Audience$Path"
}
