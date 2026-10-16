# Operational KPI contracts

Use this guide when defining a selected metric or a target. Reuse its governed definition and existing collection path. If proposing a changed denominator, eligibility rule or window, name a new version and its effect on comparisons; do not silently rewrite the baseline. Keep detail proportional to the decision rather than adding every field to every answer.

## Define what is counted

For each recommended KPI, driver or guardrail, record the decision and responsible role, desired direction, exact calculation and unit, entity and deduplication key, eligible population/exclusions, source and definition version, reporting window/timezone, and review cadence. For ratios, specify numerator and denominator populations and their relationship. A percentage needs a defined base; an average needs its weighting. Review cadence and event/cohort window are different concepts.

For conversion or retention, define cohort entry, outcome horizon, and the event-time/ingestion cutoff needed before calling it mature. Compare cohorts at equivalent observation horizons. A recent cohort with fewer days of follow-up is provisional; do not count its unobserved future outcomes as failures. Use existing reliable keys and authoritative events before proposing new instrumentation.

## Preserve aggregation and interpretation

Compute a pooled rate from appropriately deduplicated numerator and denominator totals at the stated grain, not a simple average of subgroup percentages. Do not sum distinct counts across overlapping populations, or join events at a finer grain and multiply the counted entity. If the inputs cannot support the required aggregation, explain the missing keys or coverage.

Keep material segment rates and denominators visible when composition changes could explain aggregate movement. An aggregate increase can coexist with deterioration in every segment. This is a diagnosis to investigate, not proof of a causal intervention. For an experiment, propose checks of assignment/observation units, allocation, instrumentation, guardrails and uncertainty; a pre/post comparison alone does not establish causal lift.

## Distinguish availability states

- Verified coverage and positive denominator: calculate the metric within the recorded scope; zero observed successes may be a real zero.
- Verified coverage and no eligible denominator: report null / no eligible population, not 0%.
- Missing instrumentation, unavailable source or unknown coverage: report unknown / not measured, not zero activity.
- Incomplete cohort, reporting window or watermark: label the estimate provisional and state what must mature before comparison.

Keep measured values, proposed definitions and unmeasured quantities distinct. Continue conceptual design without inventing baselines or requiring live data for a task explicitly limited to supplied evidence.

## Connect targets and guardrails to decisions

Separate an observed baseline, an aspirational target, a provisional planning range and an approved decision threshold. State the baseline's definition/window, target horizon, unit, anchor, assumptions and decision owner. Distinguish relative percentage changes from percentage-point changes. If an anchor is too weak, specify the measurement or feasibility evidence needed instead of inventing a firm target or a plausible-looking range.

For each material guardrail, specify the direction of harm, population/window, proposed tolerance and review action. Mark an unsupported tolerance as a proposal needing calibration. Do not infer that an unmeasured guardrail passed. For an experiment, relate the minimum useful effect and uncertainty method to the decision before claiming a sample size, significance or sufficient duration; use appropriate analysis for that design rather than a universal fixed cutoff.

Identify the existing event/query path, accountable role, check/reconciliation to perform, cadence and action on failure. A written measurement plan does not mean events, queries, alerts or rollouts were executed or authorized. Preserve the requested output format; these contracts support it rather than selecting another deliverable.

Primary background checked 2026-10-16: [dbt ratio metrics](https://docs.getdbt.com/docs/build/ratio) illustrates explicit numerator/denominator and filters; [Google Analytics CohortSpec](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/CohortSpec) distinguishes cohort selection from follow-up; [Microsoft pre-experiment patterns](https://www.microsoft.com/en-us/research/articles/patterns-of-trustworthy-experimentation-pre-experiment-stage/) connects hypotheses, units and metrics; [Microsoft post-experiment patterns](https://www.microsoft.com/en-us/research/articles/patterns-of-trustworthy-experimentation-post-experiment-stage/) discusses denominator and telemetry changes. This general authoring guide is a local synthesis, not a claim that a vendor enforces every rule above.
