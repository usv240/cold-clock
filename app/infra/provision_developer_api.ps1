param(
  [Parameter(Mandatory = $true)][string]$ProjectId
)

$ErrorActionPreference = "Stop"
$SecretId = "developer-api-pepper"
$ProjectNumber = gcloud projects describe $ProjectId --format "value(projectNumber)"
$ServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"

gcloud services enable secretmanager.googleapis.com --project $ProjectId --quiet

$ExistingSecret = gcloud secrets list --project $ProjectId --format "value(name)" | Where-Object { $_ -eq $SecretId }
if (-not $ExistingSecret) {
  gcloud secrets create $SecretId --project $ProjectId --replication-policy automatic --quiet
}

$Versions = gcloud secrets versions list $SecretId --project $ProjectId --format "value(name)"
if (-not $Versions) {
  $PepperBytes = New-Object byte[] 32
  $Random = [Security.Cryptography.RandomNumberGenerator]::Create()
  $Random.GetBytes($PepperBytes)
  $Random.Dispose()
  $Pepper = [Convert]::ToBase64String($PepperBytes)
  $Pepper | gcloud secrets versions add $SecretId --project $ProjectId --data-file=- --quiet
  $Pepper = $null
  $PepperBytes = $null
}

gcloud secrets add-iam-policy-binding $SecretId `
  --project $ProjectId `
  --member "serviceAccount:$ServiceAccount" `
  --role "roles/secretmanager.secretAccessor" `
  --quiet

Write-Host "Secret Manager is ready. Deploy scripts pin API_KEY_PEPPER to developer-api-pepper:1."

