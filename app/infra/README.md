# ColdClock cloud infrastructure

`firestore.indexes.json` contains the two composite indexes used by transactional wake scans: pending wakes by due time and expired leases by expiry time.

`provision_scheduler.ps1` idempotently creates or updates `cold-clock-wake-scan`. The enabled job calls `POST /internal/wakes/scan` every minute using a Google-signed OIDC token from the dedicated scheduler service account. The application verifies audience, issuer, service-account email, and email verification before claiming work. The worker uses deterministic actions, leases, bounded retry, and retained dead letters.

The public deployment uses a simulated clock only for an explicitly labelled judge demonstration. Production deployments should remove or operator-protect the public time-advance route.
