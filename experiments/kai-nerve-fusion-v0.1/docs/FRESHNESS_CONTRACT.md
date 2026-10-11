# Freshness Contract v1

Separate:
1. process health;
2. publication age;
3. source observation age;
4. transport age.

Perception legacy:
effective_age_ms = frame_age_ms + file_age_ms

Physical actuation additionally requires session_id, monotonic source_seq, selected provenance, known source age and effective age within budget.

fresh: may satisfy only the freshness prerequisite.
stale: budget exceeded/source unhealthy.
unknown: missing session/provenance/age; never moves.
replay: repeated/backwards seq in same session; never moves.

New session_id may restart sequence; the transition must be logged.
