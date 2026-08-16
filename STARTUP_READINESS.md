# ColdClock Startup Readiness

## Current level

ColdClock is a deployed **synthetic operational pilot**, not production clinical software. The deterministic
sample proves the safety state machine; the pilot workspace proves that the same system accepts
multiple cases and event-shaped user inputs.

## Working now

- Multi-case Firestore persistence and queue.
- Synthetic case intake on the public service. Authorized de-identified mode is disabled by default and reserved for a separately secured deployment.
- Verbatim package evidence and user-confirmed label provenance.
- Configurable monitoring range with no AI medication disposition.
- Idempotent sensor-event ingestion using unique device event IDs.
- Real-time pilot audit timestamps.
- Named human review with independently entered rationale.
- Approval-gated sandbox fulfillment, delivery, and receipt.
- Authenticated scheduler worker, tracing, failure recovery, and executable safety proofs.

## Required before PHI or clinical use

1. Customer identity, role-based authorization, and tenant-isolated storage.
2. Customer-specific HIPAA analysis and an executed Google Cloud BAA where applicable.
3. Validated device, pharmacy, payer, and logistics connectors with reconciliation.
4. Clinical safety, usability, accessibility, and human-factors validation.
5. Regulatory classification review based on final intended use and claims.
6. Incident response, backup/restore tests, retention/deletion rules, SLOs, and support ownership.
7. A real authorized pilot with predeclared operational measures. No health-outcome claim without
   appropriate evidence.

## Official references

- HHS HIPAA Security Rule: https://www.hhs.gov/hipaa/for-professionals/security/index.html
- HHS authentication and audit-control protocol: https://www.hhs.gov/hipaa/for-professionals/compliance-enforcement/audit/protocol/index.html
- FDA Clinical Decision Support Software guidance (January 2026): https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software
- Google Cloud HIPAA guidance and covered products: https://cloud.google.com/security/compliance/hipaa/
- HL7 FHIR MedicationDispense: https://hl7.org/fhir/MedicationDispense.html
- HL7 FHIR DeviceMetric: https://hl7.org/fhir/DeviceMetric.html

These references shape engineering and validation requirements. They are not legal advice,
regulatory clearance, clinical validation, or evidence that ColdClock is HIPAA compliant.
