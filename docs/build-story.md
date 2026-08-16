# ColdClock: the work after the refrigerator alarm

I created this piece of content for the purposes of entering the All Things Agentic Hackathon.

Most cold-chain tools end at an alert. ColdClock begins there. It turns a synthetic home medicine excursion into a verified evidence packet, stops at a named pharmacist decision, and only then coordinates sandbox replacement and accessible delivery.

The difficult engineering was failure behavior: missing temperature history produces no invented reading; an unavailable reviewer preserves the clinical gate; unavailable stock produces no substitution; a courier failure lets a named human choose recovery. Firestore wake rows use deterministic IDs, transactional leases, bounded retry, and dead letters. Cloud Run handles the service, Gemini 3.5 Flash reads the synthetic package, Firestore persists the case, and Cloud Trace correlates requests.

The public demo proves execution, not clinical outcomes. Every person, lot, pharmacy, and courier is synthetic. A qualified professional remains the only medication-disposition authority.

Try it: https://cold-clock-109051079423.us-central1.run.app

