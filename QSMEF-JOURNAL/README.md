# QSMEF — Computational Implementation

**QSMEF** (*Quantum Software Engineering Module Evaluation Framework*) is a framework for assessing the functional contributions of blocks in quantum circuits. This repository provides its Python computational implementation, including applicability checks, coalition-based evaluation, Shapley-value attribution, a granularity recommendation assistant, and reproducible case-study executions.

The main executable is **`QSMEF_Implementation.py`**.

## Scope

The implementation supports:

- Representation of quantum experiments through a common `QSMEFCase` specification (initial state, operations, functional players, execution order, observable, constraints, and semantic contract).
- Applicability assessment of the initial state, unitary operations, Hermitian observable, coalition states, real expectation values, functional constraints, and executable semantic invariants.
- Identity neutralization of omitted functional blocks while retaining the order of the remaining operations.
- Coalition values relative to the empty-coalition baseline, `v(C) = M_H(C) - M_H(∅)`, and Shapley-value calculation for applicable cases.
- A granularity assistant for considering contiguous groupings of functional blocks under declared analysis objectives and coalition budgets.
- Multicase orchestration and reports that distinguish numerical verification from assumptions or declarations.

**Interpretation note:** An `APPLICABLE` verdict means that the implemented checks and the *declared* semantic criteria hold for the specified case. It is not an independent proof of every aspect of functional equivalence. For operations supplied as functions, unitarity may be declared by construction rather than verified from an explicit matrix.

## Included case studies

1. QAOA–MaxCut (cycle graph C6, depth p = 2).
2. TwoLocal–H₂ (four-qubit Jordan–Wigner representation, with BFGS optimization of 12 variational parameters).
3. SKW quantum walk search on a hypercube.
4. QPE–Shor (with continued-fraction-based classical postprocessing).
5. Graph Partitioning / Minimum Bisection (fixed Hamming-weight subspace and XY mixer).

The main execution also evaluates a modified SKW oracle and performs a controlled comparison between the original and modified oracle using a shared initial state.

Some cases are intentionally reported as **`NOT APPLICABLE UNDER THE DECLARED SCOPE`**. Such outcomes are part of the applicability analysis and do not necessarily indicate software failures.

## Requirements

- Python 3.10 or newer (recommended).
- NumPy, SciPy, pandas, and Matplotlib (listed in `requirements.txt`).
- IPython is optional; the script falls back to standard `print` output if IPython is unavailable.

The implementation was syntax-checked with Python 3.13.5. An example environment used NumPy 2.3.5, SciPy 1.17.0, pandas 2.2.3, and Matplotlib 3.10.8. These versions document one environment, not a guarantee of identical results across every supported installation.

## Installation

Download or clone the repository and open a terminal in the directory containing `QSMEF_Implementation.py` and `requirements.txt`.

Optionally, create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\activate
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows, `py` can be used instead of `python` if that is how Python is installed.

## Run the experiments

From the same directory, execute:

```bash
python QSMEF_Implementation.py
```

The `__main__` block calls:

```python
run_journal_experiments(show_tables=False)
compare_skw_oracle_versions(show_tables=False)
```

The program prints case configurations, applicability verdicts, and experiment outputs. The script is computationally intensive in some cases, including the H₂ variational optimization and quantum-walk calculations; execution time depends on the machine.

To save terminal output to a text file:

```bash
python QSMEF_Implementation.py > qsmef_run.log 2>&1
```

## Use from Python

The implementation can also be imported as a module without running the complete experiment suite:

```python
from QSMEF_Implementation import (
    build_maxcut_case,
    validate_qsmef_case,
    compute_shapley_values,
)

case = build_maxcut_case()
validation = validate_qsmef_case(case, show_tables=False)
shapley = compute_shapley_values(case, validation, show_table=False)
```

The main script computes Shapley values only for cases deemed applicable. When using the API directly, inspect `validation["verdict"]` before interpreting any attribution results.

## Reproducibility and methodological boundaries

- Coalition values are evaluated against the same case-specific initial state and observable, using the declared operation schedule.
- Missing functional blocks are neutralized by identity (i.e., skipped without changing the position or order of the remaining operations).
- The Shapley computation uses the coalition value function relative to the empty coalition.
- Semantic contracts are explicitly specified for each case; their executable checks support, but do not replace, the methodological justification of functional comparability.
- The granularity assistant uses declared goals and heuristic candidate ranking; its recommendations should not be interpreted as globally optimal decompositions.
- Numerical outputs can depend on floating-point behavior, installed library versions, and optimization settings.

For a publication, preserve the exact code version and record the software environment used to produce the reported tables. If archiving the repository with Zenodo, cite the DOI associated with the specific archived release.

## File layout

```text
QSMEF-Quantum-CaseStudies/
├── QSMEF_Implementation.py
├── README.md
└── requirements.txt
```

The computational implementation is distributed as a single Python script; no package installation or additional project-specific modules are required for the default execution.
