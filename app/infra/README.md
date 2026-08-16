# ColdClock cloud infrastructure

`firestore.indexes.json` contains the two composite indexes used by transactional wake scans: pending wakes by due time and expired leases by expiry time. The service itself remains the idempotent worker; Cloud Scheduler may call `POST /api/hardening/scan-due` on a fixed cadence.

The public deployment uses a simulated clock only for an explicitly labelled judge demonstration. Production deployments should disable the public advance route or protect it with an authenticated operator gateway.
