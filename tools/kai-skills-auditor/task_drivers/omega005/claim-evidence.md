# Claim and refresh checks

Before final handoff or a data revision, keep a short private mapping for the
consequential title, summary, findings, and recommendations. Use existing source
metadata and supporting artifacts; do not add another visible report section
unless the reader needs it.

For each material claim, record:

- Stable component/narrative IDs and the exact reviewed query IDs.
- Population, period, grain, units, numerator/denominator, and comparison where
  relevant. Independently recompute the decisive result from the reviewed rows.
- Evidence cutoff separately from preparation/execution time. Set `report.asOf`
  only when the evidence supports that common calendar cutoff; otherwise retain
  truthful preparation metadata and per-source dates.
- Classification: observation, accounting contribution, interpretation, scenario,
  or recommendation. A changed population mix can change an aggregate while
  subgroup results move differently; reconcile these before claiming improvement.

On revision, compare the prior and replacement evidence and mark each affected
claim retained, revised, removed, or unresolved, with a concrete reason. Recheck
the opening, numbers, comparisons, caveats, and recommendations together. Preserve
unrelated user copy, stable IDs, layout, and presentation. Rebuilding alone cannot
refresh a stale conclusion, and a later run time cannot refresh an evidence cutoff.

Construct each `sourceRowsByQuery` map only from that component's declared query
IDs and current reviewed rows. Validate the map using the runtime's existing
provenance checks; do not attach all report queries to every paragraph, silently
join sources, or treat an accepted binding as proof that the prose is true.

Missing values, unavailable comparisons, and zero denominators retain their
specific meaning. Record unresolved material claims and the exact missing
evidence; avoid inventing values or recommending an intervention solely because
an aggregate changed. This check is a reasoning aid, not an automated natural
language correctness certificate.
