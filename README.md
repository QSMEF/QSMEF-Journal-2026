# QSMEF — Quantum Software Engineering Module Evaluation Framework

## Overview

QSMEF is a framework for evaluating the functional contributions of components in quantum software.

The framework represents selected functional blocks of a quantum circuit as players in a cooperative game and uses the Shapley value to attribute changes in a defined functional metric.

QSMEF combines quantum-state evaluation, admissibility checks, executable semantic contracts, and functional contribution analysis.

The framework does not assume that every quantum algorithm or circuit decomposition is suitable for Shapley-based attribution. Applicability must first be established under the declared evaluation scope.

## Methodological Framework

A QSMEF evaluation is defined by:

- A quantum algorithm or circuit configuration.
- A set of functional blocks selected as players.
- A fixed execution schedule.
- An initial quantum state.
- A Hermitian observable defining the evaluated property.
- A coalition-neutralization policy.
- Functional constraints and an executable semantic contract.

For each coalition \(C\), the validator constructs the corresponding circuit configuration and evaluates the resulting quantum state \(\rho_C\).

The functional metric is:

\[
M_H(\rho_C)=\operatorname{Tr}(H\rho_C)
\]

The characteristic function is defined relative to the empty coalition:

\[
v(C)=M_H(\rho_C)-M_H(\rho_{\emptyset})
\]

The Shapley value assigns to each functional block its weighted average marginal contribution across coalitions.

The sign of a Shapley value indicates whether a block increases or decreases the defined metric on average. Its interpretation depends on the observable and the functional property being evaluated.

## Applicability Validation

QSMEF distinguishes technical validity from functional and semantic admissibility.

The validator evaluates:

1. **Technical conditions:** valid quantum states, unitary operations, compatible dimensions, and real-valued observable expectations.
2. **Functional constraints:** executable conditions associated with the declared problem domain.
3. **Semantic contracts:** formalizable invariants supporting a common interpretation of coalition results.

The researcher specifies the functional meaning and formalizable criteria. The validator evaluates those criteria across coalitions and reports the evidence.

If the required conditions are not satisfied, the framework does not interpret the resulting Shapley values as valid functional attributions under the declared scope.

## Implemented Case Studies

The implementation includes five quantum software case studies.

| Case study | Evaluated property | Applicability |
|---|---|---|
| SKW quantum walk | Expectation of an energy-like observable associated with the quantum walk | Applicable |
| QAOA–MaxCut, C6, p=2 | Expectation of the declared cost Hamiltonian | Applicable |
| TwoLocal–H2 | Electronic energy subject to the two-electron sector constraint | Not applicable under the declared scope |
| QPE/Shor | Phase-estimation functionality under the declared semantic contract | Not applicable under the declared scope |
| Graph Partitioning — Minimum Bisection | Expected number of cut edges under a fixed-cardinality constraint | Applicable |

The implementation also includes an SKW experiment using a modified oracle phase to examine changes in functional attribution under a controlled configuration.

These results are specific to the implemented configurations, functional decompositions, observables, and admissibility contracts.

## Repository Contents

- `qsmef_validatorV1.0.py` — QSMEF validator, case constructors, applicability analysis, Shapley-value computation, and experimental execution.

## Requirements

The implementation uses Python and the following scientific libraries:

- NumPy
- Pandas
- SciPy
- Matplotlib

The script also supports notebook-style table display when IPython is available.

Install the dependencies using:

```bash
python -m pip install numpy pandas scipy matplotlib ipython
```

## Running the Experiments

Download or clone this repository.

Run the validator using:

```bash
python qsmef_validatorV1.0.py
```

The script executes the five case studies and the modified-oracle SKW comparison.

Alternatively, import the module and execute the experimental pipeline:

```python
from qsmef_validatorV1_0 import run_journal_experiments
```

**Note:** The repository filename contains a period in its version identifier. To import it as a standard Python module, first rename a local copy to `qsmef_validatorV1_0.py`.

Then run:

```python
results = run_journal_experiments(show_tables=False)
```

Set `show_tables=True` to display detailed validation and contribution tables.

The experimental pipeline uses the predefined case configurations without enabling the optional granularity assistant.

## Interpretation of Results

For applicable cases, the framework computes functional contributions using the Shapley value.

For non-applicable cases, the validator reports the conditions that prevent attribution under the declared scope.

A non-applicability verdict does not imply that the underlying quantum algorithm is invalid. It indicates that the selected decomposition, neutralization policy, functional domain, or semantic contract does not support the required comparison across all coalitions.

## Scope and Limitations

QSMEF evaluates functional contributions relative to a declared configuration and observable.

The interpretation of its results depends on the selected functional granularity and semantic contract.

Exact coalition enumeration has exponential complexity in the number of players, making the choice of functional granularity important for computational feasibility.

The included experiments use simulated quantum-state evolution and do not establish performance under physical quantum hardware noise.

## Reproducibility

The source code contains the case configurations, observables, functional constraints, semantic criteria, and procedures required to execute the implemented experiments.

Reproduction of the reported results requires preserving the corresponding configurations and evaluation assumptions.

---
## Citation and Archived Release

QSMEF v1.0.0 is permanently archived on Zenodo to support reproducibility and scientific citation.

**Version-specific DOI (v1.0.0):** https://doi.org/10.5281/zenodo.23325320

**Concept DOI (all versions):** https://doi.org/10.5281/zenodo.23325319

**Suggested citation:**

Pezzini, M. C. (2026). *QSMEF v1.0.0 — Quantum Software Engineering Module Evaluation Framework: Validator and Reproducible Case Studies* (Version 1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23325320

The version-specific DOI identifies the exact archived software release used for the reported experiments. The concept DOI provides a persistent reference to the software across future versions.
**QSMEF — Quantum Software Engineering Module Evaluation Framework**
