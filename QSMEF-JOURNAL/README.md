# QSMEF — Computational Implementation and Reproducibility

**QSMEF** (*Quantum Software Engineering Module Evaluation Framework*) is a framework for evaluating functional contributions of blocks in quantum circuits through coalition-based observable measurements and Shapley values, subject to explicitly declared applicability conditions. This repository accompanies the QSMEF journal manuscript and provides its computational implementation, experimental records, and regression tests.

## Scope and interpretation

QSMEF represents a case through `QSMEFCase`: an initial state, ordered operations, functional blocks (players), an observable, functional constraints, and an executable semantic contract. Omitted functional blocks are neutralized by identity while the prescribed operation order is retained. Coalition values are defined relative to the empty coalition, `v(C) = M_H(C) - M_H(∅)`, and Shapley values are calculated when the case satisfies the declared applicability checks.

The validator distinguishes four outcomes:

- `APPLICABLE`
- `NOT APPLICABLE UNDER THE DECLARED SCOPE`
- `SEMANTIC CONTRACT REQUIRED`
- `SPECIFICATION ERROR`

An `APPLICABLE` verdict establishes that the implemented checks and declared criteria were satisfied for the specified configuration. It does **not** independently certify complete semantic comparability. A negative verdict under the declared scope does not establish universal non-applicability. Some technical properties of function-supplied operations may rely on explicit construction assumptions rather than exhaustive matrix verification.

The implementation also provides a granularity recommendation assistant based on declared objectives and computational constraints; its recommendations are heuristic, not globally optimality-certified.

## Case studies

1. **QAOA–MaxCut:** cycle graph C6, depth `p = 2`.
2. **TwoLocal–H₂:** four-qubit Jordan–Wigner representation and a two-electron-sector restriction.
3. **SKW quantum walk:** search on a hypercube with oracle, coin, and shift blocks.
4. **QPE–Shor:** phase estimation associated with modular period finding; applicability is evaluated under a declared semantic criterion.
5. **Graph partitioning / minimum bisection:** fixed Hamming-weight sector and XY mixer.

Two modified-oracle SKW comparisons are distinguished: **full evolution**, in which the oracle modification affects state preparation, and **fixed-state comparison**, in which the oracle interventions share the same reference state. These experiments address different questions and their Shapley attributions must not be conflated.

## Files

The executable artifacts are in `QSMEF-JOURNAL/resultados/`:

| File | Purpose |
| --- | --- |
| `QSMEF_Implementation.py` | Framework implementation and experiment entry point |
| `test_qsmef_regression.py` | Nine automated regression tests |
| `qsmef_checks.json` | Previously recorded numerical reference values and expected verdicts |
| `requirements_qsmef.txt` | Python dependencies for the reproducibility package |
| `ejecutar_pruebas.bat` | Windows test runner |
| `README_pruebas_QSMEF.txt` | Additional test execution instructions |
| `qsmef_regression_run.log` | Recorded successful test execution |
| `experiment_summary.csv` | Summary of experiments and applicability outcomes |
| `verification_results.txt` | Summary of previously recorded verification outcomes |

The repository also contains a `revisión_literatura/` directory with materials associated with the literature review. These are separate from the computational regression suite.

## Installation

Install Python and the dependencies listed in `requirements_qsmef.txt`. From the `QSMEF-JOURNAL/resultados/` directory:

```bash
python -m pip install -r requirements_qsmef.txt
```

A virtual environment is recommended for a clean installation. Exact numerical results may vary slightly across operating systems, Python/library versions, and numerical optimization settings.

## Run the experiments

From `QSMEF-JOURNAL/resultados/`:

```bash
python QSMEF_Implementation.py
```

To save console output:

```bash
python QSMEF_Implementation.py > qsmef_run.log 2>&1
```

The main script includes orchestration of the journal case studies and SKW oracle comparisons. Some calculations, including numerical optimization, may take longer depending on the machine.

## Run the regression tests

From `QSMEF-JOURNAL/resultados/`:

```bash
python -m unittest -v test_qsmef_regression.py
```

On Windows, alternatively double-click `ejecutar_pruebas.bat` **after extracting or cloning the repository**. Keep the implementation, test script, JSON reference, and dependency file together in the same directory.

The regression suite contains **nine tests**, covering the five core case studies, the full-evolution and controlled fixed-state SKW comparisons, a rejected unsupported QPE configuration, and a MaxCut granularity check. It checks applicability verdicts, coalition counts, numerical Shapley references, and Shapley efficiency where applicable. For the modified full-evolution SKW experiment, the suite additionally checks approximately `φ_O = 0.134201` and `Δφ_O = 0.387256` (absolute tolerance `2e-5`).

The reference JSON is a previously recorded computational baseline, **not an external independent validation**. A successful test run supports computational consistency and reproducibility under the tested configurations; it does not independently prove all methodological or semantic assumptions.

**Filename consistency:** `test_qsmef_regression.py` must refer to `QSMEF_Implementation.py` and `qsmef_checks.json`, matching the filenames in this repository. These two import/reference lines should be verified after downloading the published release.

## Scientific and methodological boundaries

- Functional contributions depend on the selected circuit configuration, observable, block granularity, and baseline.
- Identity neutralization preserves the specified operation schedule but does not, by itself, establish functional comparability.
- Executable semantic criteria are declared by the researcher and checked by the validator; passing them does not constitute an independent proof that the criteria are sufficient for every interpretation.
- For QPE/Shor, the negative result concerns the declared criterion and configuration, not universal non-applicability or a general impossibility of phase estimation.
- The granularity assistant offers heuristic suggestions rather than certified globally optimal decompositions.
- Numerical differences may arise from floating-point precision and optimization behavior.

## Citation and archival version

For scientific use, cite the **specific Zenodo release DOI** corresponding to the exact GitHub version used for the reported results. Do not substitute a DOI from an earlier release without checking that its archived source and test artifacts match the manuscript.

The software and records are intended to support transparent inspection and reproducibility of the published QSMEF experiments.
