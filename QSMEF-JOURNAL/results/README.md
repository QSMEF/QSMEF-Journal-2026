# QSMEF — Journal reproducibility release

This archive contains the implementation and reproducibility check for the QSMEF case studies.

## Run

Python 3.10+ is recommended. Install dependencies with:

```bash
python -m pip install -r requirements.txt
```

Run the case studies:

```bash
python QSMEF_Implementation.py
```

Run numerical consistency checks:

```bash
python verify_release.py
```

## Scientific scope

- QAOA–MaxCut C6: four players, Shapley contributions to the fixed observable.
- SKW: three players (O, G, S); article's modified-oracle comparison re-evolves the walk for 19 steps with phase 0.70*pi. An auxiliary fixed-state comparison is also present; these are different experiments.
- QPE/Shor: 128 coalitions; semantic admissibility requires pairwise distinguishability of ideal candidate eigenphases under retained controlled powers and reference preparation. This is NOT a proof of output-level identifiability, classical period recovery, or universal non-applicability of QSMEF. The fixed-outcome-window observable is not the period-recovery probability.
- TwoLocal–H2 and Minimum Bisection are also included.

A `NOT APPLICABLE UNDER THE DECLARED SCOPE` verdict means the case fails the **specified** contract, not that the mathematical game or Shapley values are universally undefined.

## Reproducibility

This release is a minimally cleaned derivative of `QSMEF_Implementation(8).py`. The unused legacy QPE semantic criterion equating fixed-window probability with successful period recovery was removed; the continued-fractions outcome diagnostic remains. Core computations and experimental parameters are unchanged.

The check script checks reported verdicts, QPE coalition counts, QAOA Shapley values, SKW reference and full-evolution modified-oracle values, and efficiency. It is a regression check, not independent physical validation.
