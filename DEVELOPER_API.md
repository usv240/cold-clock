# ColdClock Developer API

The hosted UI remains keyless for judges. Integrations use the stable, authenticated `/v1` API.

## Get a free key

```bash
curl -X POST "$BASE_URL/api/developer/keys" \
  -H "Content-Type: application/json" \
  -d '{"label":"evaluation","acceptable_use_acknowledgement":true}'
```

The key is displayed once and is valid for 180 days. The server persists only an HMAC digest. A keyed network fingerprint—not a raw client address—is used for abuse control.

Each key and originating network fingerprint may make 50 authenticated requests per UTC day. Every `/v1` response includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`. Issuance allows up to five keys per network fingerprint per UTC day so evaluators behind a shared network are not locked out; all keys still share the 50-call network ceiling.

## Use the service

```bash
curl -X POST "$BASE_URL/v1/tabletop-runs" -H "X-API-Key: $API_KEY"
```

For input-driven use, create a case with `POST /v1/cases`, send an idempotent sensor event, record the qualified review decision, and later send the receipt event. ColdClock automatically executes all permitted transitions between those legitimate external boundaries. See `/docs` for request schemas and `GET /v1/cases/{case_id}/autonomy-proof` for derived execution proof.

The public deployment accepts synthetic data only. Authorized de-identified data is supported only when `ALLOW_DEIDENTIFIED_PILOT=true` in a protected deployment. Do not send PHI to the public service. ColdClock does not make medication-use decisions.

## Security and durability

- API-key and IP-fingerprint digests use a pepper injected from Google Secret Manager.
- Firestore transactions atomically enforce key issuance and both quota scopes.
- Resource IDs are unguessable; the API exposes no cross-customer list endpoint.
- Cloud Run, Firestore, Cloud Scheduler, Cloud Trace, Gemini 3.5 Flash, and Gemini Embedding 001 power the deployed workflow.

