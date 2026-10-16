# QSMEF — Computational Implementation

**QSMEF** (*Quantum Software Engineering Module Evaluation Framework*) is a framework for assessing the functional contributions of blocks in quantum circuits. This repository provides its Python computational implementation, including applicability checks, coalition-based evaluation, Shapley-value attribution, a granularity recommendation assistant, and reproducible case-study executions.

The executable currently published in this repository is **`QSMEF_Implementation.py`**, located in **`QSMEF-JOURNAL/resultados/`**. All commands below assume execution from the `QSMEF-JOURNAL/` directory unless otherwise stated.

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

1. **QAOA–MaxCut:** Cycle graph C6, depth p = 2.
2. **TwoLocal–H₂:** Four-qubit Jordan–Wigner representation, with BFGS optimization of 12 variational parameters.
3. **SKW quantum walk:** Quantum search on a hypercube.
4. **QPE–Shor:** Quantum phase estimation with continued-fraction-based classical postprocessing.
5. **Graph Partitioning / Minimum Bisection:** Fixed Hamming-weight subspace and XY mixer.

The implementation also examines a modified SKW oracle. **Two SKW comparisons must be distinguished:**

- **Full-evolution comparison:** the original and modified oracle configurations are evolved separately, so the comparison includes the effect of the modified oracle throughout the walk.
- **Fixed-state comparison:** the oracle variants are evaluated with a shared reference state; this is an auxiliary comparison and does not represent a complete re-evolution under the modified oracle.

These experiments answer different questions and their Shapley values must not be treated as interchangeable.

Some cases are intentionally reported as **`NOT APPLICABLE UNDER THE DECLARED SCOPE`**. Such outcomes are part of the applicability analysis and do not necessarily indicate software failures or universal non-applicability of QSMEF.

## Requirements

- Python 3.10 or newer (recommended).
- NumPy, SciPy, pandas, and Matplotlib (listed in the `requirements.txt` at the root of `QSMEF-JOURNAL/`).
- IPython is optional; the script falls back to standard `print` output if IPython is unavailable.

The implementation was syntax-checked with Python 3.13.5. An example environment used NumPy 2.3.5, SciPy 1.17.0, pandas 2.2.3, and Matplotlib 3.10.8.

These versions document one environment, not a guarantee of identical results across every supported installation.

## Installation

Download or clone the repository. From the repository root, navigate to `QSMEF-JOURNAL`:

```bash
cd QSMEF-JOURNAL
```

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

Install dependencies using the root requirements file:

```bash
python -m pip install -r requirements.txt
```

On Windows, `py` can be used instead of `python` if that is how Python is installed.

## Run the experiments

From `QSMEF-JOURNAL/`, execute:

```bash
python resultados/QSMEF_Implementation.py
```

The main execution is documented as invoking:

```python
run_journal_experiments(show_tables=False)
compare_skw_oracle_versions(show_tables=False)
```

The program prints case configurations, applicability verdicts, and experiment outputs. Some computations, including the H₂ variational optimization and quantum-walk calculations, may be intensive; execution time depends on the machine.

To save terminal output to a text file:

```bash
python resultados/QSMEF_Implementation.py > qsmef_run.log 2>&1
```

## Experimental results and verification records

The `resultados/` directory currently contains the implementation and accompanying documentation and outputs:

- **`QSMEF_Implementation.py`:** Python implementation and experiment entry point.
- **`experiment_summary.csv`:** Structured summary of the evaluated cases, applicability verdicts, and computed functional contributions where reported.
- **`verification_results.txt`:** Stored verification record. Its contents should be interpreted according to the checks actually recorded in that file.
- **`README.md` and `requirements.txt`:** Additional documentation and dependency information maintained within `resultados/`.

The repository's root `README.md` and `requirements.txt` provide the primary entry point for readers following these instructions.

The summary distinguishes the **SKW full-evolution modified-oracle experiment** from the **auxiliary fixed-state comparison**. Both should be retained with explicit labels in any scientific report.

Reference results support traceability and reproducibility, but they are not independent verification of every methodological assumption or semantic interpretation. Numerical differences may arise from floating-point precision, installed library versions, and optimization behavior.

### Optional regression-check script

A separate `verify_release.py` script can be included to check expected numerical results and verdicts against the published implementation. **This script is not part of the repository structure shown here and should not be described as an available command until it has been uploaded and its import paths have been checked.** A successful regression check does not establish independent physical or semantic validity.

## Use from Python

Because the executable is located inside `resultados/`, add that directory to Python's module search path when importing from `QSMEF-JOURNAL/`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "resultados"))

from QSMEF_Implementation import (
    build_maxcut_case,
    validate_qsmef_case,
    compute_shapley_values,
)

case = build_maxcut_case()
validation = validate_qsmef_case(case, show_tables=False)

if validation["verdict"] == "APPLICABLE":
    shapley = compute_shapley_values(
        case,
        validation,
        show_table=False,
    )
```

The main script computes Shapley values only for cases deemed applicable. When using the API directly, inspect `validation["verdict"]` before interpreting any attribution results.

## Reproducibility and methodological boundaries

- Coalition values are evaluated against the same case-specific initial state and observable, using the declared operation schedule.
- Missing functional blocks are neutralized by identity (i.e., skipped without changing the position or order of the remaining operations).
- The Shapley computation uses the coalition value function relative to the empty coalition.
- Semantic contracts are explicitly specified for each case; their executable checks support, but do not replace, the methodological justification of functional comparability.
- The granularity assistant uses declared goals and heuristic candidate ranking; its recommendations should not be interpreted as globally optimal decompositions.
- Numerical outputs can depend on floating-point behavior, installed library versions, and optimization settings.
- The applicability verdict is specific to the declared configuration, functional property, granularity, and semantic scope.
- The QPE/Shor verdict concerns the stated semantic contract and does not establish universal non-applicability, output-level identifiability, or successful classical period recovery.

For a scientific publication, preserve the exact code version and software environment used to produce the reported results. When archiving the repository with Zenodo, cite the DOI associated with the specific archived release.

## Repository structure

The following tree reflects the files visible in the GitHub repository at the time of this README update:

```text
QSMEF-Journal-2026/
├── QSMEF-JOURNAL/
│   ├── README.md
│   ├── requirements.txt
│   └── resultados/
│       ├── QSMEF_Implementation.py
│       ├── README.md
│       ├── experiment_summary.csv
│       ├── requirements.txt
│       └── verification_results.txt
│
└── revisión_literatura/
    ├── datos/
    │   ├── retrieved_studies.csv
    │   ├── excluded_studies.csv
    │   └── selected_studies_analysis.xlsm
    └── README.md
```

The `QSMEF-JOURNAL/` directory contains the computational materials and instructions. The `revisión_literatura/` directory contains the bibliographic data and analysis supporting the literature review associated with QSMEF.

The computational implementation is distributed as a Python script. No package installation or additional project-specific modules are required for the default execution, subject to the dependencies listed above.

## Scientific use

QSMEF provides a systematic computational procedure for assessing the applicability of functional contribution analysis to quantum circuit components.

The implementation combines coalition-based evaluation with Shapley-value attribution under explicitly declared functional and semantic conditions.

Its results must be interpreted with respect to the selected circuit configuration, observable, functional decomposition, and applicability criteria.

The implementation and accompanying experimental outputs are provided to support scientific transparency, inspection, and reproducibility.
