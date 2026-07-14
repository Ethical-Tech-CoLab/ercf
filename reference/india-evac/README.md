# Evacuation Readiness & Uncertainty Simulator

A single-file, dependency-free research instrument that models how field-intelligence uncertainty degrades civilian evacuation decisions in armed conflict — built for a PhD project on civilian protection. All data is synthetic and reproducible from a seed number; no real locations or real datasets are used.

**This is the primary/canonical repository.** [`indiaclarke03-ops/EvacSimulator`](https://github.com/indiaclarke03-ops/EvacSimulator) mirrors this tool but should be treated as downstream — develop here first.

## Run it

No build step. Open `index.html` in a browser, or serve the folder statically:

```
python3 -m http.server 8000
# then open http://localhost:8000/index.html
```

## What it does

Generates synthetic evacuation destinations and evacuee groups from a seed, scores each destination's readiness across seven factors (three of them non-substitutable "gatekeepers" — Security, Authority consent, Willingness — any of which can hard-cap readiness at 20%), runs 500 Monte Carlo trials per group–destination pair to turn that readiness into a success-probability distribution, and assigns each group to its best-scoring available destination. A "Field Uncertainty" slider degrades every factor's confidence simultaneously, making it possible to watch predicted outcomes fall apart in real time as an information environment worsens — with no underlying condition on the ground actually changing.

A key design point: the model distinguishes an **unassessed** factor ("Unknown") from a **confirmed exclusion** ("Unwilling", for a host community that has explicitly declined) — conflating the two would make an unresolvable refusal look like a solvable intelligence gap. See [CONCEPT.md](CONCEPT.md) for the full reasoning behind this and the other modelling choices.

## Files

| File | Purpose |
|---|---|
| `index.html` | The tool itself — UI, simulation engine, and an in-page Methodology accordion |
| `explainer.html` | Narrative walkthrough of the model, linked from "About this tool" and the "?" links throughout the tool |
| `Evacuation_Simulator_Methodology.docx` | Full formula derivations, rationale, and academic/IHL citations — authoritative if it and the in-app docs ever disagree |
| `CONCEPT.md` | The research problem, the readiness model, and the epistemic distinctions the tool insists on |
| `ARCHITECTURE.md` | How it's actually built — execution pipeline, state, configuration surface |
| `BACKLOG.md` | Open issues and suggested next steps from a close read of the code and methodology doc |

## Reproducibility

Every output is fully determined by four values: seed, number of destinations (N), number of evacuee groups (M), and uncertainty level. The **Copy link** button writes all four into the page URL and copies it to your clipboard — pasting that URL anywhere and opening it regenerates the exact same scenario. Cite outputs as `seed=42, N=8, M=3, uncertainty=30%` (see the methodology doc's Reproducibility Protocol for the full citation format).

## Status

Conceptual demonstration tool for thesis research, not an operational decision-support system. Outputs require empirical calibration before any real-world use — see the Assumptions & Limitations section in the Methodology accordion (in-app) or §10 of the methodology document.
