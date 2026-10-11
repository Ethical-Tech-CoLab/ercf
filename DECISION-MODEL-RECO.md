# Decision-model recommendation: research evidence assistance only

Date: 2026-10-11. Status: proposed offline research aid.
Scope: this repository. Public sources; no operational deployment proposed.

## Existing decision-support boundary

Reviewed [README](https://github.com/Ethical-Tech-CoLab/ercf/blob/befed0ff552b11d75ad49971e28afff576b434ae/README.md),
revision `befed0ff552b11d75ad49971e28afff576b434ae`.
This is a README-led assessment, not a validation of the underlying model.

ERCF is decision support, not action prescription. Its fixed-dimensional
scoring and logistics calculations must remain transparent. Its mortality
outputs are indicative rather than predictive, and historical calibration
has structural limitations.

## Narrow recommendation

Consider a decision model only **before analysis**, to route public background
documents to a research taxonomy or flag a source/claim mismatch for a human
analyst. Preserve source, timestamp, reporting period and uncertainty.

Use relevant / not relevant / insufficient evidence for routing, and supports /
contradicts / not established for a cited claim. A source-ranking experiment
must evaluate candidate recall before discarding any material.

Do not use a decision model to issue evacuation instructions, set action
thresholds, estimate mortality probability, invent missing measurements,
override logistics calculations or adjudicate whether a route is safe.
Do not turn cheaper API inference into a safety gate.

## Methods to compare

Begin with human evidence review, lexical search and deterministic validation.
Jev's [citation-checking pattern](https://docs.typesafe.ai/cookbooks/citation_check.md)
is a possible offline research aid; Microsoft-Decision-1 and Sage are comparison
candidates on the same approved public records, not qualified safety systems.
A licensed local classifier may avoid external processing but still needs
task-specific validation.

The named proprietary models do not expose exact downloadable checkpoints in
the researched public documentation. No claim of local operational availability
or performance is made.

## Evaluation and stopping conditions

Use case/source/time-disjoint public research examples with stale reports,
conflicting periods, missing observations, unsupported causal claims and
region-specific terminology. Have independent analysts adjudicate relevance
and citation support; preserve disagreement.

Measure false reassurance, relevant-source recall, unsupported-claim acceptance,
calibration, review time and full accepted-record cost. Treat missed or
under-documented cases explicitly. Do not infer validated predictive skill
from a small curated support-checking sample.

Hard gate: numerical inputs, calculations and application outputs remain
unchanged. Any output accidentally entering action advice stops the pilot.
No individual-level sensitive data or live emergency workflow is in scope.

## Next step

Run an offline annotated-source study and retain the original human workflow.
Only a demonstrated improvement in evidence review, under explicit domain
approval, justifies an opt-in assistant. This is not a recommendation to replace
or extend ERCF's operational decision logic.
