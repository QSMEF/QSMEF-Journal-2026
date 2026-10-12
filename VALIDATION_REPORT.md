# QSMEF — Computational Validation Report

## Purpose

This report documents the reproducibility check of the QSMEF journal validator and its five declared quantum case studies. The validation was performed on the Python file `qsmef_validatorV1.0.py` downloaded from the `QSMEF-Journal-2026` repository.

## How to reproduce

Install the Python dependencies listed in `requirements.txt`, then run from the repository root:

```bash
python qsmef_validatorV1.0.py
```

The script calls `run_journal_experiments(show_tables=False)`, which runs all five declared cases without invoking the optional granularity assistant, followed by the modified-oracle SKW comparison. For an interactive Python session, the same entry point can be called with `show_tables=True` to display detailed tables.

## Results

| Case | Players | Coalitions | Applicability verdict | Shapley computation |
|---|---:|---:|---|---|
| QAOA–MaxCut C6, p=2 | 4 | 16 | APPLICABLE | Computed |
| TwoLocal–H2 (4 qubits) | 5 | 32 | NOT APPLICABLE UNDER THE DECLARED SCOPE | Not computed |
| SKW hypercube (n=8, t=19) | 3 | 8 | APPLICABLE | Computed |
| QPE/Shor (N=21, a=2, m=5) | 7 | 128 | NOT APPLICABLE UNDER THE DECLARED SCOPE | Not computed |
| Graph Partitioning (Minimum Bisection, n=6) | 2 | 4 | APPLICABLE | Computed |

The reported coalition counts follow from exhaustive enumeration of the declared player sets (2^L coalitions for L players). The two non-applicable cases are deliberately retained as evidence of the framework's declared-scope checks; Shapley attribution is not performed when the applicability conditions fail.

### Selected numerical outputs

- **QAOA–MaxCut C6:** C1 = −1.583908; B1 = −0.416092; C2 = −0.416092; B2 = −1.583908 (rounded to six decimal places).
- **SKW, original oracle:** O = −0.253055; G = 0.015528; S = 0.015528 (rounded to six decimal places).
- **Minimum Bisection:** C_fase = −0.519224; M_XY = 0.472962 (rounded to six decimal places).
- **Modified SKW oracle (0.70π):** the modified case returned `APPLICABLE`; its Shapley efficiency residual was approximately 1.388 × 10⁻¹⁷.

## Verification performed

1. Parsed the uploaded Python source successfully using Python's `ast` parser.
2. Executed the complete script as a standalone Python program; the process exited with status code 0.
3. Confirmed that the five case-study verdicts were produced and that the additional modified-SKW experiment completed.
4. Confirmed that the program withholds Shapley results for the two non-applicable cases.

## Scope and limitations

- The results concern the **declared case configurations**, observables, neutralization policy, and executable semantic criteria; they are not claims of algorithm-independent functional equivalence.
- The simulations are idealized and do not constitute hardware-noise validation.
- Exhaustive coalition enumeration has exponential scaling, O(2^L) case evaluations before accounting for the cost of each circuit/state evaluation.
- Some methodological conditions are justified by construction or case-specific declarations, while executable checks verify the formalizable constraints. These categories should not be conflated.
- The source emits a non-fatal `SyntaxWarning` about an invalid escape sequence in a documentation string containing LaTeX notation. This does not affect the observed execution, but can be cleaned up in a subsequent maintenance revision.
- This report records a local execution check, not a formal proof of implementation correctness or cross-platform reproducibility.

## Reproducibility note

For archival reproducibility, record the Python interpreter version and installed package versions when creating a tagged release. Preserve the validated script and its `requirements.txt` together in the same release.
