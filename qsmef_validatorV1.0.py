# -*- coding: utf-8 -*-
# 
from __future__ import annotations
import contextlib
import io
import itertools
from dataclasses import dataclass, field
from math import factorial, log2
from typing import Any, Callable, Mapping, Optional, Sequence, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
try:
    from IPython.display import display
except ImportError:
    display = print



import itertools
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

try:
    from IPython.display import display
except ImportError:
      display = print


# AUXILIARY TYPES

Array = np.ndarray

# Function that takes a quantum state and returns the state
# obtained after applying an operation.
ApplyFunction = Callable[[Array], Array]

# Function used to evaluate the functional observable.
ObservableFunction = Callable[[Array, str], complex]

# Function used to check a case constraint.
ConstraintFunction = Callable[
    [Array, str, float],
    tuple[bool, float, str]
]

# Function used to check a semantic criterion.
SemanticCriterionFunction = Callable[
    [Array, str, frozenset[str], complex, float],
    tuple[bool, float, str],
]


# HELPER FUNCTIONS

def _dagger(matrix: Array) -> Array:
    'Return the conjugate transpose (adjoint) of a matrix.\n\nThe adjoint is obtained by complex conjugation and transposition.'
    return np.asarray(matrix, dtype=complex).conj().T


def _max_abs(matrix: Array) -> float:
    'Return the largest absolute entry of an array.\n\nUsed to quantify numerical residuals in validation checks.'
    values = np.asarray(matrix)
    return float(np.max(np.abs(values))) if values.size else 0.0


def _coalition_label(
    indices: Sequence[int],
    names: Sequence[str]
) -> str:
    'Build a readable coalition label, such as ∅, {R0}, or {R0, E0}.'
    if not indices:
        return "∅"

    return "{" + ", ".join(
        names[index] for index in indices
    ) + "}"


# OPERATION SPECIFICATION

@dataclass(frozen=True)
class OperationSpec:
    'Describe a quantum circuit operation.\n\nThe operation can be supplied as a matrix or as a function acting directly on a quantum state. When ``declared_unitary=True``, unitarity is justified by construction rather than checked through an explicit matrix. This is useful for large operations such as the SKW shift.'

    action: Union[Array, ApplyFunction]

    # Indicates whether the operation is declared unitary by construction.
    declared_unitary: bool = False

    # Rationale for considering the operation unitary
    # without a numerical matrix-based check.
    unitarity_rationale: str = ""

    def is_matrix(self) -> bool:
        'Return whether the operation is provided as a matrix.'
        return not callable(self.action)

    def apply(
        self,
        state: Array,
        state_kind: str
    ) -> Array:
        'Apply the operation to a quantum state.\n\nFunction-based operations support state vectors only. Matrix operations act as U|ψ> on state vectors and UρU† on density matrices.'

        # Case 1: the operation is implemented as a function.
        if callable(self.action):

            if state_kind != "statevector":
                raise ValueError(
                    'Function-based operations only support state vectors.'
                )

            return np.asarray(
                self.action(state),
                dtype=complex
            )

        # Case 2: the operation is represented by a matrix.
        matrix = np.asarray(
            self.action,
            dtype=complex
        )

        if state_kind == "statevector":
            # State-vector evolution:
            # |ψ'> = U|ψ>
            return matrix @ state

        # Density-matrix evolution:
        # ρ' = UρU†
        return matrix @ state @ _dagger(matrix)

# ADMISSIBILITY CONSTRAINT SPECIFICATION

@dataclass(frozen=True)
class ConstraintSpec:
    'Describe an executable admissibility constraint.\n\nEach constraint has a name, an evaluator, and an optional description. It is checked for every coalition state.'

    name: str
    evaluator: ConstraintFunction
    description: str = ""

    def evaluate(
        self,
        state: Array,
        state_kind: str,
        tolerance: float
    ) -> tuple[bool, float, str]:
        'Evaluate the constraint on a quantum state.\n\nReturn a pass/fail flag, the numerical value, and a description.'

        passed, value, detail = self.evaluator(
            state,
            state_kind,
            tolerance
        )

        return bool(passed), float(value), str(detail)


# PROJECTOR-BASED CONSTRAINT

def projector_constraint(
    name: str,
    projector: Array,
    description: str = "",
) -> ConstraintSpec:
    'Create a projector-based constraint.\n\nRequire the state to lie in the subspace defined by P: <ψ|P|ψ> = 1 for a state vector, or Tr(Pρ) = 1 for a density matrix, within numerical tolerance.'

    P = np.asarray(
        projector,
        dtype=complex
    )

    def evaluator(
        state: Array,
        state_kind: str,
        tolerance: float
    ) -> tuple[bool, float, str]:

        # If the state is represented by a vector |ψ>,
        # compute <ψ|P|ψ>.
        if state_kind == "statevector":
            value = float(
                np.real(
                    np.vdot(
                        state,
                        P @ state
                    )
                )
            )

        # If the state is represented by a density matrix ρ,
        # compute Tr(Pρ).
        else:
            value = float(
                np.real(
                    np.trace(
                        P @ state
                    )
                )
            )

        # The ideal condition is value = 1.
        # The residual measures the deviation from that value.
        residual = abs(
            1.0 - value
        )

        # The constraint is satisfied when the residual
        # falls within the allowed numerical tolerance.
        return (
            residual <= tolerance,
            value,
            f"residuo={residual:.3e}"
        )

    return ConstraintSpec(
        name=name,
        evaluator=evaluator,
        description=description
    )

@dataclass(frozen=True)
class SemanticCriterion:
    ##A formalizable semantic invariant evaluated for every coalition.

    name: str
    evaluator: SemanticCriterionFunction
    description: str = ""

    def evaluate(
        self,
        state: Array,
        state_kind: str,
        coalition: frozenset[str],
        expected: complex,
        tolerance: float,
    ) -> tuple[bool, float, str]:
        passed, value, detail = self.evaluator(
            state, state_kind, coalition, expected, tolerance
        )
        return bool(passed), float(value), str(detail)


@dataclass(frozen=True)
class SemanticContract:
 ##  Executable support for a common interpretation across coalitions.

##The researcher specifies the semantic scope in ``description`` and
##provides formalizable invariants in ``criteria``. The validator,
##rather than the researcher, determines whether all coalitions satisfy
##those invariants.

    description: str = ""
    criteria: Sequence[SemanticCriterion] = field(default_factory=tuple)


def semantic_projector_criterion(
    name: str,
    projector: Array,
    description: str = "",
) -> SemanticCriterion:
   ##Require every coalition state to remain in the declared subspace.
    P = np.asarray(projector, dtype=complex)

    def evaluator(
        state: Array,
        state_kind: str,
        coalition: frozenset[str],
        expected: complex,
        tolerance: float,
    ) -> tuple[bool, float, str]:
        del coalition, expected
        if state_kind == "statevector":
            value = float(np.real(np.vdot(state, P @ state)))
        else:
            value = float(np.real(np.trace(P @ state)))
        residual = abs(1.0 - value)
        return residual <= tolerance, value, f"residuo={residual:.3e}"

    return SemanticCriterion(name=name, evaluator=evaluator, description=description)


def semantic_interval_criterion(
    name: str,
    lower: float,
    upper: float,
    description: str = "",
) -> SemanticCriterion:
    ##Require the common observable to remain within the declared numerical range.

    low = float(lower)
    high = float(upper)
    if low > high:
        raise ValueError('The lower bound cannot exceed the upper bound.')

    def evaluator(
        state: Array,
        state_kind: str,
        coalition: frozenset[str],
        expected: complex,
        tolerance: float,
    ) -> tuple[bool, float, str]:
        del state, state_kind, coalition
        value = float(expected.real)
        imaginary_ok = abs(expected.imag) <= tolerance
        interval_ok = low - tolerance <= value <= high + tolerance
        detail = (
            f"intervalo=[{low:.6g}, {high:.6g}], "
            f"parte_imaginaria={expected.imag:.3e}"
        )
        return imaginary_ok and interval_ok, value, detail

    return SemanticCriterion(name=name, evaluator=evaluator, description=description)


@dataclass(frozen=True)
class QSMEFCase:
    ##Algorithm-independent standard input contract for QSMEF validation.
    ##``operations`` includes both player and fixed operations.
    ##``players`` identifies operations that coalitions may neutralize.
    ##Any operation in ``schedule`` that is not a player
    ##remains fixed across all coalitions.

    name: str
    initial_state: Array
    operations: Mapping[str, Union[OperationSpec, Array, ApplyFunction]]
    players: Sequence[str]
    schedule: Sequence[str]
    observable: Union[Array, ObservableFunction]
    constraints: Sequence[ConstraintSpec] = field(default_factory=tuple)
    semantic_contract: SemanticContract = field(default_factory=SemanticContract)
    property_description: str = "No especificada"
    tolerance: float = 1e-10


def _normalize_operations(
    operations: Mapping[str, Union[OperationSpec, Array, ApplyFunction]]
) -> dict[str, OperationSpec]:
    normalized: dict[str, OperationSpec] = {}
    for raw_name, raw_operation in operations.items():
        name = str(raw_name)
        if name in normalized:
            raise ValueError(f"Operación repetida: {name}")
        normalized[name] = (
            raw_operation
            if isinstance(raw_operation, OperationSpec)
            else OperationSpec(raw_operation)
        )
    if not normalized:
        raise ValueError('The case must declare at least one operation.')
    return normalized


def _check_state(
    state: Array, tolerance: float
) -> tuple[str, bool, float, float]:
    state = np.asarray(state, dtype=complex)
    if state.ndim == 1:
        norm = float(np.real(np.vdot(state, state)))
        residual = abs(norm - 1.0)
        return "statevector", residual <= tolerance, norm, residual

    if state.ndim == 2 and state.shape[0] == state.shape[1]:
        hermiticity = _max_abs(state - _dagger(state))
        trace_value = np.trace(state)
        trace_residual = float(abs(trace_value - 1.0))
        eigenvalues = np.linalg.eigvalsh((state + _dagger(state)) / 2)
        minimum = float(np.min(eigenvalues).real)
        valid = (
            hermiticity <= tolerance
            and trace_residual <= tolerance
            and minimum >= -tolerance
        )
        return "density_matrix", valid, float(np.real(trace_value)), max(
            hermiticity, trace_residual, max(0.0, -minimum)
        )

    raise ValueError(
        'initial_state must be a state vector or a square density matrix.'
    )


def _expectation(
    observable: Union[Array, ObservableFunction],
    state: Array,
    state_kind: str,
) -> complex:
    if callable(observable):
        return complex(observable(state, state_kind))
    H = np.asarray(observable, dtype=complex)
    if state_kind == "statevector":
        return complex(np.vdot(state, H @ state))
    return complex(np.trace(H @ state))


def _validate_qsmef_case_core(case: QSMEFCase, show_tables: bool = True) -> dict[str, Any]:
   ##Validate a QSMEFCase instance without algorithm-specific logic.
    tolerance = float(case.tolerance)
    if tolerance <= 0:
        raise ValueError('Tolerance must be positive.')

    state0 = np.asarray(case.initial_state, dtype=complex)
    state_kind, initial_valid, initial_value, initial_residual = _check_state(
        state0, tolerance
    )
    dimension = state0.shape[0]
    operations = _normalize_operations(case.operations)
    players = [str(name) for name in case.players]
    schedule = [str(name) for name in case.schedule]

    specification_errors: list[str] = []
    if len(players) != len(set(players)):
        specification_errors.append('The player list contains duplicates.')
    unknown_players = sorted(set(players) - set(operations))
    unknown_schedule = sorted(set(schedule) - set(operations))
    if unknown_players:
        specification_errors.append(f"Jugadores no definidos: {unknown_players}")
    if unknown_schedule:
        specification_errors.append(
            f"Operaciones de la secuencia no definidas: {unknown_schedule}"
        )
    if not schedule:
        specification_errors.append('The execution schedule is empty.')
    unused_players = sorted(set(players) - set(schedule))
    if unused_players:
        specification_errors.append(
            f"Jugadores que no aparecen en la secuencia: {unused_players}"
        )

    observable_hermitian: Optional[bool]
    observable_residual: float
    if callable(case.observable):
        observable_hermitian = None
        observable_residual = np.nan
    else:
        H = np.asarray(case.observable, dtype=complex)
        if H.shape != (dimension, dimension):
            specification_errors.append(
                f"El observable tiene dimensión {H.shape}; "
                f"se esperaba {(dimension, dimension)}."
            )
        observable_residual = _max_abs(H - _dagger(H))
        observable_hermitian = observable_residual <= tolerance

    operation_rows: list[dict[str, Any]] = []
    all_operations_unitary = True
    for name, operation in operations.items():
        role = "player" if name in players else "fixed"
        if operation.is_matrix():
            matrix = np.asarray(operation.action, dtype=complex)
            if matrix.shape != (dimension, dimension):
                specification_errors.append(
                    f"La operación {name} tiene dimensión {matrix.shape}; "
                    f"se esperaba {(dimension, dimension)}."
                )
                unitary = False
                residual = np.inf
                evidence = 'invalid dimension'
            elif operation.declared_unitary:
                unitary = True
                residual = np.nan
                evidence = 'declared: ' + (
                    operation.unitarity_rationale or 'without written justification'
                )
            else:
                identity = np.eye(dimension, dtype=complex)
                residual = max(
                    _max_abs(_dagger(matrix) @ matrix - identity),
                    _max_abs(matrix @ _dagger(matrix) - identity),
                )
                unitary = residual <= tolerance
                evidence = 'matrix verification'
        else:
            unitary = bool(operation.declared_unitary)
            residual = np.nan
            evidence = 'declared: ' + (
                operation.unitarity_rationale or 'required for a function-based operation'
            )
        all_operations_unitary = all_operations_unitary and unitary
        operation_rows.append(
            {
                "operación": name,
                "rol": role,
                "apariciones": schedule.count(name),
                "unitaria": unitary,
                "evidencia_unitariedad": evidence,
                "residuo_unitariedad": residual,
            }
        )

    operations_df = pd.DataFrame(operation_rows)

    if specification_errors:
        verdict = 'SPECIFICATION ERROR'
        reason = " ".join(specification_errors)
        report = {
            "case": case.name,
            "verdict": verdict,
            "reason": reason,
            "specification_errors": specification_errors,
            "operations": operations_df,
            "coalitions": pd.DataFrame(),
            "constraints": pd.DataFrame(),
        }
        print(f"RESULTADO: {verdict}\nMOTIVO: {reason}")
        return report

    coalition_rows: list[dict[str, Any]] = []
    constraint_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    for size in range(len(players) + 1):
        for indices in itertools.combinations(range(len(players)), size):
            coalition_players = {players[index] for index in indices}
            state = state0.copy()
            for operation_name in schedule:
                is_player = operation_name in players
                if is_player and operation_name not in coalition_players:
                    continue
                state = operations[operation_name].apply(state, state_kind)

            _, state_valid, norm_or_trace, state_residual = _check_state(
                state, tolerance
            )
            expected = _expectation(case.observable, state, state_kind)
            expected_is_real = abs(expected.imag) <= tolerance
            coalition = _coalition_label(indices, players)

            coalition_constraints_pass = True
            for constraint in case.constraints:
                passed, value, detail = constraint.evaluate(
                    state, state_kind, tolerance
                )
                coalition_constraints_pass = coalition_constraints_pass and passed
                constraint_rows.append(
                    {
                        "coalición": coalition,
                        "restricción": constraint.name,
                        "cumple": passed,
                        "valor": value,
                        "detalle": detail,
                    }
                )

            coalition_semantics_pass = bool(case.semantic_contract.criteria)
            coalition_set = frozenset(coalition_players)
            for criterion in case.semantic_contract.criteria:
                passed, value, detail = criterion.evaluate(
                    state, state_kind, coalition_set, expected, tolerance
                )
                coalition_semantics_pass = coalition_semantics_pass and passed
                semantic_rows.append(
                    {
                        "coalición": coalition,
                        "criterio_semántico": criterion.name,
                        "cumple": passed,
                        "valor": value,
                        "detalle": detail,
                    }
                )

            coalition_rows.append(
                {
                    "coalición": coalition,
                    "tamaño": size,
                    "estado_válido": state_valid,
                    "norma_o_traza": norm_or_trace,
                    "residuo_estado": state_residual,
                    "M_H": float(expected.real),
                    "parte_imaginaria": float(expected.imag),
                    "valor_real": expected_is_real,
                    "restricciones_cumplidas": coalition_constraints_pass,
                    "contrato_semántico_cumplido": coalition_semantics_pass,
                }
            )

    coalitions_df = pd.DataFrame(coalition_rows)
    constraints_df = pd.DataFrame(constraint_rows)
    semantics_df = pd.DataFrame(semantic_rows)
    baseline = float(
        coalitions_df.loc[coalitions_df["coalición"] == "∅", "M_H"].iloc[0]
    )
    coalitions_df["v(C)"] = coalitions_df["M_H"] - baseline

    all_states_valid = bool(coalitions_df["estado_válido"].all())
    all_values_real = bool(coalitions_df["valor_real"].all())
    all_constraints_pass = bool(coalitions_df["restricciones_cumplidas"].all())
    semantic_contract_specified = bool(case.semantic_contract.criteria)
    all_semantic_criteria_pass = bool(
        coalitions_df["contrato_semántico_cumplido"].all()
    )
    technical_admissible = (
        initial_valid
        and all_operations_unitary
        and observable_hermitian is not False
        and all_states_valid
        and all_values_real
    )
    automatic_admissible = technical_admissible and all_constraints_pass

    if not technical_admissible:
        verdict = 'NOT APPLICABLE UNDER THE DECLARED SCOPE'
        failed = []
        if not initial_valid:
            failed.append('invalid initial state')
        if not all_operations_unitary:
            failed.append('non-unitary operations')
        if observable_hermitian is False:
            failed.append('non-Hermitian observable')
        if not all_states_valid:
            failed.append('invalid coalition states')
        if not all_values_real:
            failed.append('non-real expectation values')
        reason = ", ".join(failed) + "."

    elif not all_constraints_pass:
       verdict = 'NOT APPLICABLE UNDER THE DECLARED SCOPE'
       failed_constraints = constraints_df.loc[
        ~constraints_df["cumple"],
        ["coalición", "restricción"]
       ]
       reason = (
        "Functional constraints are not satisfied in "
        f"{len(failed_constraints)} coalition(s). "
        "Therefore, the declared functional scope is not satisfied."
       )


    elif not semantic_contract_specified:
        verdict = 'SEMANTIC CONTRACT REQUIRED'
        reason = (
            'Technical conditions hold, but the case does not specify executable semantic invariants.'
        )
    elif not all_semantic_criteria_pass:
         verdict = 'NOT APPLICABLE UNDER THE DECLARED SCOPE'
         reason = (
              'Semantic contract criteria do not hold for every coalition; the common functional interpretation required by the declared scope is therefore not preserved.'
        )

    else:

        verdict = 'APPLICABLE'

        reason = (
            'Technical conditions, functional constraints, and all semantic contract invariants are satisfied.'
        )


    summary_df = pd.DataFrame(
        [
            {
                "nivel": "Specification",
                "condición": "Complete case",
                "resultado": True
            },
            {
                "nivel": "Automatic",
                "condición": "Valid initial state",
                "resultado": initial_valid
            },
            {
                "nivel": "Automatic",
                "condición": "Operaciones unitarias",
                "resultado": all_operations_unitary
            },
            {
                "nivel": "Automatic",
                "condición": "Observable hermitiano",
                "resultado": observable_hermitian
            },
            {
                "nivel": "Automatic",
                "condición": "Valid states",
                "resultado": all_states_valid
            },
            {
                "nivel": "Automatic",
                "condición": "Valores esperados reales",
                "resultado": all_values_real
            },
            {
                "nivel": "Constraints",
                "condición": "Todas satisfechas",
                "resultado": all_constraints_pass
            },
            {
                "nivel": "Semantic",
                "condición": "Contrato especificado",
                "resultado": semantic_contract_specified
            },
            {
                "nivel": "Semantic",
                "condición": "Same state space",
                "resultado": all_states_valid
            },
            {
                "nivel": "Semantic",
                "condición": "Same case observable",
                "resultado": True
            },
            {
                "nivel": "Semantic",
                "condición": "Invariantes satisfechos",
                "resultado": all_semantic_criteria_pass
            },
        ]
    )


    print("=" * 76)
    print("QSMEF APPLICABILITY ASSISTANT")
    print("=" * 76)

    print(f"Caso: {case.name}")
    print(f"Propiedad: {case.property_description}")
    print(f"Representación: {state_kind}; dimensión: {dimension}")

    print(
        f"Jugadores: {len(players)}; "
        f"operaciones fijas: {len(set(schedule) - set(players))}"
    )

    print(
        f"Pasos de ejecución: {len(schedule)}; "
        f"coaliciones: {len(coalitions_df)}"
    )

    print(f"Baseline: {baseline:.12f}")
    print(f"RESULT: {verdict}")
    print(f"REASON: {reason}\n")


    if show_tables:

        print('SUMMARY')
        display(summary_df)

        print('OPERATIONS')
        display(operations_df)

        print('COALITIONS')
        display(coalitions_df)

        if not constraints_df.empty:
            print('FUNCTIONAL CONSTRAINTS')
            display(constraints_df)

        if not semantics_df.empty:
            print('SEMANTIC CONTRACT')
            display(semantics_df)


    return {
        "case": case.name,
        "verdict": verdict,
        "reason": reason,
        "automatic_admissible": automatic_admissible,
        "summary": summary_df,
        "operations": operations_df,
        "coalitions": coalitions_df,
        "constraints": constraints_df,
        "semantics": semantics_df,
        "semantic_contract_specified": semantic_contract_specified,
        "all_semantic_criteria_pass": all_semantic_criteria_pass,
        "baseline": baseline,
    }

"""### 2.1 Multilevel validation of functional preservation

The technical validity of a coalition does not by itself imply that its result preserves the semantics of the analysis. Therefore, the verdict is organized into three levels:

1. **Specification invariants:** same instance, initial state, encoding, observable, fixed operations, measurement, postprocessing, and neutralization policy.
2. **Transformation invariants:** preservation of the subspace, relevant symmetries, order, functional dependencies, and block interfaces.
3. **Resulting-state invariants:** valid quantum state, domain membership, and preservation of physical or combinatorial constraints.

The methodological rule is

\[
\operatorname{Adm}(C)\iff
\operatorname{ValQ}(U_C)\land
\operatorname{Est}(U_C)\land
\rho_C\in\mathcal D\land
\operatorname{Sem}\!\left(M_H(\rho_C)\right)=\operatorname{Sem}_H.
\]

QSMEF is applicable only when all coalitions satisfy the declared technical, functional, and semantic conditions.

When a case lacks an executable semantic contract to verify the common interpretation of partial configurations, the validator reports `SEMANTIC CONTRACT REQUIRED` and does not compute Shapley contributions.

When a functional constraint or semantic-contract criterion fails for any coalition, the result is `NOT APPLICABLE UNDER THE DECLARED SCOPE`.

"""


# MULTILEVEL FUNCTIONAL PRESERVATION VALIDATION

from dataclasses import dataclass
from typing import Optional
import contextlib
import io


@dataclass(frozen=True)
class FunctionalValidationProfile:
    'Additional methodological contract for interpreting a case family.'

    family: str
    instance: str
    encoding: str
    measurement: str
    postprocessing: str
    neutralization: str
    domain: str
    dependencies: str
    semantic_basis: str
    semantic_decidable: bool


def _case_family(case_name: str) -> str:
    name = case_name.lower()
    if "maxcut" in name:
        return "maxcut"
    if "twolocal" in name or "h2" in name:
        return "h2"
    if "skw" in name:
        return "skw"
    if "qpe" in name or "shor" in name:
        return "qpe"
    if "partition" in name or "bisection" in name:
        return "partitioning"
    return "unknown"


VALIDATION_PROFILES = {
    "maxcut": FunctionalValidationProfile(
        family="QAOA-MaxCut",
        instance="Same C6 graph and edge set",
        encoding="Each bitstring represents a partition of the same graph",
        measurement="Same observable H_C = sum of Z_j Z_(j+1)",
        postprocessing='Expectation of H_C = sum of Z_j Z_(j+1) (minimization)',
        neutralization="Absent blocks are omitted at their original positions, equivalent to identity",
        domain="Full bitstring space of graph C6",
        dependencies="The C1-B1-C2-B2 order is preserved",
        semantic_basis=(
            "The instance and H_C remain fixed in QSMEFCase. "
            "The interval [-6,6] is a spectral bound check, not independent evidence of correspondence with the thesis."
        ),
        semantic_decidable=True,
    ),
    "h2": FunctionalValidationProfile(
        family="TwoLocal-H2",
        instance="Same H2 molecular Hamiltonian in Jordan-Wigner encoding",
        encoding="Same four spin orbitals and Hartree-Fock state",
        measurement="Same electronic Hamiltonian",
        postprocessing="Electronic energy within the N=2 sector",
        neutralization="Capas ausentes reemplazadas conceptualmente por identidad",
        domain="Subespacio de exactamente dos electrones",
        dependencies="Orden R0-E0-R1-E1-R2",
        semantic_basis="Projector P2 checks Tr(P2 rho_C) >= 1-epsilon.",
        semantic_decidable=True,
    ),
    "skw": FunctionalValidationProfile(
        family="SKW",
        instance="Same hypercube, marked vertex, time, and gamma",
        encoding="Same coin-position space and psi_t state",
        measurement="Same walk energy observable",
        postprocessing="Change in expectation from the same psi_t",
        neutralization="Absent O, G, or S blocks are neutralized without reordering",
        domain="Normalized coin-position space",
        dependencies="The functional O-G-S order is preserved",
        semantic_basis=(
            "Coalitions are interpreted as interventions on a functional step, "
            "not as full executions of the search algorithm."
        ),
        semantic_decidable=True,
    ),
    "qpe": FunctionalValidationProfile(
        family="QPE-Shor",
        instance="Mismos N, a y counting register",
        encoding="Same preparation and work register",
        measurement="Same IQFT and counting-register measurement",
        postprocessing="Interpretation as a complete phase-estimation instance",
        neutralization="Potencias controladas ausentes reemplazadas por identidad",
        domain="Complete instance with all controlled powers",
        dependencies="The declared interpretation requires the full set of U_k",
        semantic_basis=(
            "The complete_qpe_instance criterion requires all controlled powers. "
            "Partial coalitions do not satisfy the declared scope."
        ),
        semantic_decidable=True,
    ),
    "partitioning": FunctionalValidationProfile(
        family="Graph Partitioning",
        instance="Same graph and bisection condition",
        encoding="Bitstrings de peso de Hamming n/2",
        measurement="Same cut-cost Hamiltonian",
        postprocessing='Expected number of cut edges in a valid bisection',
        neutralization="Absent blocks are neutralized without changing order",
        domain="Subespacio de cardinalidad fija n/2",
        dependencies="The XY mixer preserves the feasible subspace",
        semantic_basis="Projector P_half checks the feasibility of every coalition.",
        semantic_decidable=True,
    ),
}


def _multilevel_rows(case, core_report, profile):
    coalitions = core_report["coalitions"]
    operations = core_report["operations"]

    states_valid = bool(coalitions["estado_válido"].all()) if not coalitions.empty else False
    constraints_pass = bool(coalitions["restricciones_cumplidas"].all()) if not coalitions.empty else False
    semantic_pass = bool(core_report.get("all_semantic_criteria_pass", False))
    operations_valid = bool(operations["unitaria"].all()) if not operations.empty else False

    same_schedule = len(case.schedule) > 0 and all(p in case.schedule for p in case.players)
    fixed_operations = tuple(name for name in case.schedule if name not in case.players)

    rows = [
        {
            "nivel": "A. Specification",
            "invariante": "Same problem instance",
            "cumple": True if profile else None,
            "evidencia": "BY CONSTRUCTION" if profile else "UNDETERMINED",
            "detalle": profile.instance if profile else "No case-specific profile is available.",
        },
        {
            "nivel": "A. Specification",
            "invariante": "Same initial state and encoding",
            "cumple": True if profile else None,
            "evidencia": "BY CONSTRUCTION" if profile else "UNDETERMINED",
            "detalle": profile.encoding if profile else "Encoding has not been formalized.",
        },
        {
            "nivel": "A. Specification",
            "invariante": "Same observable and measurement",
            "cumple": True if profile else None,
            "evidencia": "BY CONSTRUCTION" if profile else "UNDETERMINED",
            "detalle": profile.measurement if profile else "Measurement has not been formalized.",
        },
        {
            "nivel": "A. Specification",
            "invariante": "Same postprocessing rule",
            "cumple": (profile.semantic_decidable if profile else None),
            "evidencia": (
                "BY CONSTRUCTION" if profile and profile.semantic_decidable
                else "UNDETERMINED"
            ),
            "detalle": profile.postprocessing if profile else "Postprocessing has not been declared.",
        },
        {
            "nivel": "A. Specification",
            "invariante": "Common fixed operations",
            "cumple": True,
            "evidencia": "EXECUTABLE",
            "detalle": f"Operaciones fijas: {fixed_operations if fixed_operations else 'none'}.",
        },
        {
            "nivel": "A. Specification",
            "invariante": "Identity neutralization",
            "cumple": True,
            "evidencia": "BY CONSTRUCTION",
            "detalle": (
                profile.neutralization if profile
                else "The engine omits the absent player while preserving its logical position."
            ),
        },
        {
            "nivel": "B. Transformation",
            "invariante": "Original execution order",
            "cumple": same_schedule,
            "evidencia": "EXECUTABLE",
            "detalle": " -> ".join(case.schedule),
        },
        {
            "nivel": "B. Transformation",
            "invariante": "Compatible operations and interfaces",
            "cumple": operations_valid,
            "evidencia": "EXECUTABLE",
            "detalle": "Dimension and unitarity checked or justified for every operation.",
        },
        {
            "nivel": "B. Transformation",
            "invariante": "Functional dependencies",
            "cumple": True if profile else None,
            "evidencia": "DECLARED" if profile else "UNDETERMINED",
            "detalle": profile.dependencies if profile else "Dependencies have not been formalized.",
        },
        {
            "nivel": "B. Transformation",
            "invariante": "Required subspace or symmetry",
            "cumple": constraints_pass and semantic_pass,
            "evidencia": "EXECUTABLE",
            "detalle": profile.domain if profile else "Domain has not been formalized.",
        },
        {
            "nivel": "C. Resulting state",
            "invariante": "Valid quantum state",
            "cumple": states_valid,
            "evidencia": "EXECUTABLE",
            "detalle": "Normalization or trace, Hermiticity, and positivity as appropriate to the representation.",
        },
        {
            "nivel": "C. Resulting state",
            "invariante": "Preservation of the declared domain",
            "cumple": constraints_pass and semantic_pass,
            "evidencia": "EXECUTABLE",
            "detalle": profile.domain if profile else "Domain has not been formalized.",
        },
        {
            "nivel": "C. Resulting state",
            "invariante": "Common interpretation of the result",
            "cumple": (
                semantic_pass and profile.semantic_decidable if profile else None
            ),
            "evidencia": (
                "EXECUTABLE + METHODOLOGICAL JUSTIFICATION"
                if profile and profile.semantic_decidable
                else "UNDETERMINED"
            ),
            "detalle": profile.semantic_basis if profile else "Semantic basis has not been declared.",
        },
    ]
    return pd.DataFrame(rows)


def validate_qsmef_case(
    case: QSMEFCase,
    show_tables: bool = True
) -> dict[str, Any]:
    'Run the universal QSMEF validation procedure.\n\nAccept a QSMEFCase containing the initial state, operations, players, execution schedule, observable, functional constraints, and semantic contract. No case-specific algorithm logic is introduced here.'

    return _validate_qsmef_case_core(
        case,
        show_tables=show_tables
    )




"""## 3. Quantum case constructors

### 3.1 Graph Partitioning
"""

def build_graph_partitioning_case(
    n=6,
    edges=None,
    gamma=0.5,
    beta=0.5,
):
    'Build the QSMEF Minimum Bisection case.\n\nFor a graph G with even n, minimize the number of edges crossing a balanced partition |V0| = n/2. The physical invariant is Hamming weight n/2. Use an XY ring mixer.'

    import numpy as np

    if n % 2 != 0:
        raise ValueError("n must be even for Minimum Bisection.")

    if edges is None:
        # Default: cycle graph C_n
        edges = [(i, (i + 1) % n) for i in range(n)]

    dim = 2 ** n

    # INITIAL STATE: uniform superposition of states with Hamming weight n/2

    half = n // 2

    psi0 = np.zeros(dim, dtype=complex)
    for z in range(dim):
        if bin(z).count("1") == half:
            psi0[z] = 1.0

    # Normalization
    n_states = np.sum(np.abs(psi0) ** 2)
    psi0 = psi0 / np.sqrt(n_states)

    # PHASE OPERATOR (diagonal)

    def cost_value(z):
        'Count cut edges for bitstring z.'
        bits = [(z >> (n - 1 - q)) & 1 for q in range(n)]
        return sum(bits[i] != bits[j] for i, j in edges)

    costs = np.array([cost_value(z) for z in range(dim)])

    # Phase: exp(-i gamma H_C)
    # H_C is diagonal with eigenvalues equal to the number of cut edges
    phase_diagonal = np.exp(-1j * gamma * costs)
    C_fase = np.diag(phase_diagonal)

    # XY RING MIXER (preserves Hamming weight)
    # H_ring = sum_{u} (X_u X_{u+1} + Y_u Y_{u+1})

    I2 = np.eye(2, dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)

    def kron_all(ops):
        result = np.array([[1.0 + 0.0j]])
        for op in ops:
            result = np.kron(result, op)
        return result

    def two_qubit_op(op_a, op_b, i, j, n):
        'Apply op_a at i, op_b at j, and identities elsewhere.'
        ops = []
        for q in range(n):
            if q == i:
                ops.append(op_a)
            elif q == j:
                ops.append(op_b)
            else:
                ops.append(I2)
        return kron_all(ops)

    H_XY = np.zeros((dim, dim), dtype=complex)
    for i in range(n):
        j = (i + 1) % n
        H_XY += two_qubit_op(X, X, i, j, n)
        H_XY += two_qubit_op(Y, Y, i, j, n)

    # exp(-i beta H_XY) using matrix exponentiation
    from scipy.linalg import expm
    M_XY = expm(-1j * beta * H_XY)

    # STANDARD MIXER (does NOT preserve Hamming weight)
    # For comparison: H_std = sum X_j

    H_std = np.zeros((dim, dim), dtype=complex)
    for q in range(n):
        ops = [X if p == q else I2 for p in range(n)]
        H_std += kron_all(ops)

    M_std = expm(-1j * beta * H_std)

    # OBSERVABLE: number of cut edges

    H_cost = np.diag(costs.astype(complex))

    # PROJECTOR ONTO THE SUBSPACE WITH HAMMING WEIGHT n/2

    P_half = np.zeros((dim, dim), dtype=complex)
    for z in range(dim):
        if bin(z).count("1") == half:
            P_half[z, z] = 1.0

    # DESCRIPTIVE INFORMATION

    print('\nCase configuration: Graph Partitioning (Min Bisection)')
    print("-" * 72)

    print(f"n = {n} (número de vértices del grafo)")
    print(f"Grafo: anillo C_{n} con {len(edges)} aristas")
    print(f"Cardinalidad fija: |V0| = {half}")
    print(f"Espacio de Hilbert: dimensión {dim}")
    print(f"Estado inicial: superposición uniforme de estados con HW = {half}")
    print(f"Número de estados iniciales: {int(n_states)}")

    print('\nPhysical invariant:')
    print(f"  Peso de Hamming = {half}")

    print('\nProjector:')
    print("  P_half = sum of projectors onto states with HW = n/2")

    print("\nQSMEF players:")
    print("  C_fase = operador de fase (diagonal)")
    print("  M_XY   = mixer XY ring (preserva HW)")

    print("\nObservable:")
    print("  H_cost = number of cut edges")

    print("-" * 72)

    # SEMANTIC CONTRACT

    semantic_criterion = semantic_projector_criterion(
        name='Preservation of the n/2-cardinality sector',
        projector=P_half,
        description=(
            f"Toda coalición debe preservar el peso de Hamming = {half}. "
            "The XY mixer preserves it by construction; the standard mixer does not."
        ),
    )

    # QSMEF CASE (admissible partition)

    return QSMEFCase(
        name=f"Graph Partitioning (Min Bisection) n={n}",
        initial_state=psi0,
        operations={
            "C_fase": C_fase,
            "M_XY": M_XY,
        },
        players=["C_fase", "M_XY"],
        schedule=["C_fase", "M_XY"],
        observable=H_cost,
        constraints=[],
        semantic_contract=SemanticContract(
            description=(
                "The partition cardinality is preserved under evolution. "
                "The XY mixer satisfies the invariant."
            ),
            criteria=(semantic_criterion,),
        ),
        property_description='Expected number de aristas cortadas',
        tolerance=1e-8,
    )


print('build_graph_partitioning_case loaded successfully.')


# COMPLETE QAOA-MAXCUT C6 p=2 CONSTRUCTOR

"""### 3.2 QAOA–MaxCut

"""

def build_maxcut_case():

    n = 6

    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 0),
    ]

    # QAOA parameters p=2
    gamma1 = np.pi * 0.2052
    beta1  = np.pi * 0.1026
    gamma2 = np.pi * 0.3974
    beta2  = np.pi * 0.2948

    dim = 2 ** n

    # Basic matrices

    I2_local = np.eye(2, dtype=complex)

    X_local = np.array([
        [0, 1],
        [1, 0]
    ], dtype=complex)


    def kron_local(operators):

        result = np.array([[1.0 + 0.0j]])

        for op in operators:
            result = np.kron(result, op)

        return result


    # MaxCut cost function

    costs = np.zeros(dim)

    for z in range(dim):

        bits = [
            (z >> (n - 1 - q)) & 1
            for q in range(n)
        ]

        costs[z] = sum(
            bits[i] != bits[j]
            for i, j in edges
        )


    # Observable:
    # number of cut edges
    H_C = np.diag((len(edges) - 2.0 * costs).astype(complex))
    H_cut = np.diag(costs.astype(complex))


    # Cost operator
    # exp(-i gamma H_C)

    def cost_unitary(gamma):

        return np.diag(
            np.exp(
                -1j * gamma * np.diag(H_C)
            )
        )


    # Mixer
    # exp(-i beta X)

    def rx_beta(beta):

        return (
            np.cos(beta) * I2_local
            - 1j
            * np.sin(beta)
            * X_local
        )


    def mixer_unitary(beta):

        return kron_local([
            rx_beta(beta)
            for _ in range(n)
        ])


    # Four players

    C1 = cost_unitary(gamma1)
    B1 = mixer_unitary(beta1)

    C2 = cost_unitary(gamma2)
    B2 = mixer_unitary(beta2)


    # Initial state |+>^6

    psi0 = np.ones(
        dim,
        dtype=complex
    ) / np.sqrt(dim)


    # QAOA-MaxCut case description

    print('\nCase configuration: QAOA-MaxCut')
    print("-" * 60)

    print('Graph: C6')
    print("  C6 = cycle graph with 6 vertices and 6 edges.")

    print(f"Número de qubits: {n}")
    print("  Each graph vertex is represented by a qubit.")

    print("QAOA depth: p = 2")
    print("  p = number of QAOA cost-mixer layers.")

    print('\nQAOA parameters:')
    print(f"  gamma1 = {gamma1:.10f}  -> parámetro del operador de costo C1")
    print(f"  beta1  = {beta1:.10f}  -> parámetro del operador mixer B1")
    print(f"  gamma2 = {gamma2:.10f}  -> parámetro del operador de costo C2")
    print(f"  beta2  = {beta2:.10f}  -> parámetro del operador mixer B2")

    print('\nFunctional blocks / QSMEF players:')
    print("  C1 = first cost operation, exp(-i gamma1 H_C)")
    print("  B1 = first mixer operation, exp(-i beta1 sum X)")
    print("  C2 = second cost operation, exp(-i gamma2 H_C)")
    print("  B2 = second mixer operation, exp(-i beta2 sum X)")

    print('\nPhysical order:')
    print("  C1 -> B1 -> C2 -> B2")

    print("\nObservable:")
    print("  H_C = sum of Z_j Z_(j+1); H_cut is auxiliary")

    print("-" * 60)


    # Case construction

    return QSMEFCase(

        name="QAOA-MaxCut C6 p=2",

        initial_state=psi0,

        operations={
            "C1": C1,
            "B1": B1,
            "C2": C2,
            "B2": B2,
        },

        players=[
            "C1",
            "B1",
            "C2",
            "B2",
        ],

        schedule=[
            "C1",
            "B1",
            "C2",
            "B2",
        ],

        observable=H_C,

        constraints=(),

        semantic_contract=SemanticContract(
            description=(
                "Each coalition produces a distribution over the same "
                "bitstrings of the C6 graph and is evaluated using the same "
                "MaxCut cost function."
            ),
            criteria=(
                semantic_interval_criterion(
                    "Spectral range of H_C for the C6 cycle",
                    -float(len(edges)),
                    float(len(edges)),
                    "Expectation-range check for H_C; not sufficient on its own to establish semantic identity.",
                ),
            ),
        ),

        property_description=(
            'Expectation of H_C = sum of Z_j Z_(j+1); minimization'
        ),

        tolerance=1e-10,
    )


print('build_maxcut_case loaded successfully.')


#########################################################
# COMPLETE TWOLOCAL-H2 CONSTRUCTOR
# WITH REPRODUCIBLE OPTIMIZATION OF THETA PARAMETERS

"""### 3.3 TwoLocal–H₂

"""

def build_h2_case():

    import numpy as np
    from scipy.optimize import minimize

    # SYSTEM DIMENSION

    n = 4
    dim = 2 ** n

    # BASIC MATRICES

    I2_local = np.eye(2, dtype=complex)

    X_local = np.array([
        [0, 1],
        [1, 0],
    ], dtype=complex)

    Y_local = np.array([
        [0, -1j],
        [1j, 0],
    ], dtype=complex)

    Z_local = np.array([
        [1, 0],
        [0, -1],
    ], dtype=complex)

    H_local = (
        np.array([
            [1, 1],
            [1, -1],
        ], dtype=complex)
        / np.sqrt(2)
    )

    # KRONECKER PRODUCT

    def kron_local(operators):

        result = np.array(
            [[1.0 + 0.0j]]
        )

        for operator in operators:
            result = np.kron(
                result,
                operator
            )

        return result

    # RY ROTATION

    def ry_local(theta):

        return np.array([
            [
                np.cos(theta / 2),
                -np.sin(theta / 2),
            ],
            [
                np.sin(theta / 2),
                np.cos(theta / 2),
            ],
        ], dtype=complex)

    # PAULI OPERATOR ON FOUR QUBITS

    def pauli_term(mapping):

        operators = []

        for q in range(n):

            if q in mapping:
                operators.append(
                    mapping[q]
                )
            else:
                operators.append(
                    I2_local
                )

        return kron_local(
            operators
        )

    # CZ BETWEEN TWO QUBITS

    def cz_full(a, b):

        diagonal = np.ones(
            dim,
            dtype=complex
        )

        for z in range(dim):

            bits = [
                (
                    z >> (n - 1 - q)
                ) & 1
                for q in range(n)
            ]

            if (
                bits[a] == 1
                and bits[b] == 1
            ):
                diagonal[z] = -1.0

        return np.diag(
            diagonal
        )

    # ALL-TO-ALL CZ ENTANGLING LAYER

    def all_to_all_cz():

        U = np.eye(
            dim,
            dtype=complex
        )

        for a in range(n):

            for b in range(
                a + 1,
                n
            ):
                U = (
                    cz_full(a, b)
                    @ U
                )

        return U

    # HARTREE-FOCK INITIAL STATE
    #
    # |1100>
    #
    # H2 has two electrons.

    psi0 = np.zeros(
        dim,
        dtype=complex
    )

    psi0[
        int("1100", 2)
    ] = 1.0

# H2 ELECTRONIC HAMILTONIAN
# JORDAN-WIGNER, 4 QUBITS
#
# Source:
# Seeley, J. T., Richard, M. J., & Love, P. J. (2012).
# The Bravyi-Kitaev transformation for quantum computation
# of electronic structure.
# Journal of Chemical Physics, 137, 224109.
#
# Jordan-Wigner Hamiltonian:
# Equations (88) and (89).

    # H2 ELECTRONIC HAMILTONIAN
    # JORDAN-WIGNER, 4 QUBITS

    terms = [

        (-0.81261, {}),

        (0.171201, {
            0: Z_local,
        }),

        (0.171201, {
            1: Z_local,
        }),

        (-0.2227965, {
            2: Z_local,
        }),

        (-0.2227965, {
            3: Z_local,
        }),

        (0.16862325, {
            0: Z_local,
            1: Z_local,
        }),

        (0.12054625, {
            0: Z_local,
            2: Z_local,
        }),

        (0.165868, {
            1: Z_local,
            2: Z_local,
        }),

        (0.165868, {
            0: Z_local,
            3: Z_local,
        }),

        (0.12054625, {
            1: Z_local,
            3: Z_local,
        }),

        (0.17434925, {
            2: Z_local,
            3: Z_local,
        }),

        (-0.04532175, {
            0: Y_local,
            1: Y_local,
            2: X_local,
            3: X_local,
        }),

        (0.04532175, {
            0: X_local,
            1: Y_local,
            2: Y_local,
            3: X_local,
        }),

        (0.04532175, {
            0: Y_local,
            1: X_local,
            2: X_local,
            3: Y_local,
        }),

        (-0.04532175, {
            0: X_local,
            1: X_local,
            2: Y_local,
            3: Y_local,
        }),
    ]

    H_h2 = np.zeros(
        (dim, dim),
        dtype=complex
    )

    for coefficient, mapping in terms:
        H_h2 += (
            coefficient
            * pauli_term(mapping)
        )

    # ENTANGLING LAYERS

    E0 = all_to_all_cz()
    E1 = all_to_all_cz()

    # CONSTRUCTION OF A TWOLOCAL ROTATION LAYER
    #
    # For each qubit:
    #
    #       Ry(theta_q) H
    #

    def build_rotation_layer(theta_layer):

        operators = []

        for q in range(n):

            gate = (
                ry_local(
                    theta_layer[q]
                )
                @ H_local
            )

            operators.append(
                gate
            )

        return kron_local(
            operators
        )

    # STATE PRODUCED BY THE ANSATZ FOR A THETA VECTOR
    #
    # Architecture:
    #
    # R0 -> E0 -> R1 -> E1 -> R2
    #

    def state_from_theta(theta):

        R0_test = build_rotation_layer(
            theta[0:4]
        )

        R1_test = build_rotation_layer(
            theta[4:8]
        )

        R2_test = build_rotation_layer(
            theta[8:12]
        )

        psi = (
            R2_test
            @ E1
            @ R1_test
            @ E0
            @ R0_test
            @ psi0
        )

        return psi

    # VARIATIONAL OBJECTIVE FUNCTION
    #
    # E(theta) =
    #
    # <psi(theta)| H_h2 |psi(theta)>
    #

    def energy_from_theta(theta):

        psi = state_from_theta(
            theta
        )

        energy = np.vdot(
            psi,
            H_h2 @ psi
        )

        return float(
            np.real(
                energy
            )
        )

    # OPTIMIZATION OF VARIATIONAL PARAMETERS
    #
    # Start from theta = 0.
    #
    # theta* = arg min_theta E(theta)
    #

    theta_initial = np.zeros(
        12,
        dtype=float
    )

    optimization_result = minimize(
        energy_from_theta,
        theta_initial,
        method="BFGS",
        options={
            "maxiter": 5000,
            "gtol": 1e-8,
        },
    )

    theta = np.asarray(
        optimization_result.x,
        dtype=float
    )

    # TRACEABILITY INFORMATION

    print(
        '\nTwoLocal-H2 variational optimization'
    )

    print(
        'Initial energy:',
        energy_from_theta(
            theta_initial
        )
    )

    print(
        'Optimized energy:',
        energy_from_theta(
            theta
        )
    )

    print(
        'Theta parameters:'
    )

    print(
        theta
    )

    # FINAL CONSTRUCTION OF QSMEF PLAYERS

    R0 = build_rotation_layer(
        theta[0:4]
    )

    R1 = build_rotation_layer(
        theta[4:8]
    )

    R2 = build_rotation_layer(
        theta[8:12]
    )

    # PROJECTOR P2
    #
    # Subspace corresponding to exactly
    # two electrons.
    #
    # Hamming weight = 2

    P2 = np.zeros(
        (dim, dim),
        dtype=complex
    )

    for z in range(dim):

        if (
            bin(z).count("1")
            == 2
        ):
            P2[z, z] = 1.0

    # QSMEF CONSTRAINT

    constraint_2e = (
        projector_constraint(

            name=(
                "Sector de dos electrones"
            ),

            projector=P2,

            description=(
                "The partial configuration must "
                "remain entirely within the "
                "subespacio correspondiente a "
                "exactamente dos electrones."
            ),
        )
    )
    # TWOLOCAL-H2 CASE DESCRIPTION

    print('\nCase configuration: TwoLocal-H2')
    print("-" * 65)

    print('Physical system: H2')
    print("  H2 = neutral hydrogen molecule with 2 electrons.")

    print(f"Número de qubits: {n}")
    print("  The 4 qubits represent 4 fermionic modes under Jordan-Wigner encoding.")

    print("Initial state:")
    print("  |psi0> = |1100>")
    print("  Represents exactly 2 electrons occupying two modes.")

    print("\nTwoLocal variational architecture:")
    print("  R0 -> E0 -> R1 -> E1 -> R2")
    print("  R0, R1, R2 = rotation layers.")
    print("  E0, E1 = all-to-all CZ entangling layers.")

    print('\nVariational parameters:')
    print("  theta = (theta0, ..., theta11)")
    print("  There are 12 Ry gate angles.")
    print("  Distribution:")
    print("    R0 <- theta0, theta1, theta2, theta3")
    print("    R1 <- theta4, theta5, theta6, theta7")
    print("    R2 <- theta8, theta9, theta10, theta11")

    print('\nOptimization:')
    print('  Method: BFGS')
    print("  Objective: minimize <psi(theta)| H_H2 |psi(theta)>")
    print("  The optimized theta parameters fix the specific R0, R1, and R2 operations.")

    print("\nHamiltonian:")
    print("  H_H2 = electronic Hamiltonian of H2 in Jordan-Wigner encoding.")
    print("  It is used as the case observable.")

    print("\nPropiedad funcional evaluada:")
    print('  Expectation of H_H2 = electronic energy.')

    print('\nFunctional blocks / QSMEF players:')
    print("  R0 = first rotation layer")
    print("  E0 = primera capa de entrelazamiento")
    print("  R1 = second rotation layer")
    print("  E1 = segunda capa de entrelazamiento")
    print("  R2 = third rotation layer")

    print('\nPhysical constraint:')
    print("  P2 = projector onto the exactly-two-electron sector.")
    print("  For every coalition C, the following must hold:")
    print("  Tr(P2 rho_C) >= 1 - epsilon")

    print('\nSemantic contract:')
    print("  Electronic energy is compared only across configurations")
    print("  that remain in the same physical two-electron sector.")

    print("-" * 65)


    # QSMEF CASE

    return QSMEFCase(

        name=(
            "TwoLocal-H2 "
            "4 qubits"
        ),

        initial_state=psi0,

        operations={
            "R0": R0,
            "E0": E0,
            "R1": R1,
            "E1": E1,
            "R2": R2,
        },

        players=[
            "R0",
            "E0",
            "R1",
            "E1",
            "R2",
        ],

        schedule=[
            "R0",
            "E0",
            "R1",
            "E1",
            "R2",
        ],

        observable=H_h2,

        constraints=[
            constraint_2e
        ],

        semantic_contract=SemanticContract(

            description=(
                "Electronic energy is compared only "
                "within the physical sector of exactly "
                "dos electrones."
            ),

            criteria=(
                semantic_projector_criterion(
                    "Preservation of the two-electron sector",
                    P2,
                    (
                        "Every coalition must satisfy "
                        "Tr(P2 rho_C) >= 1-epsilon."
                    ),
                ),
            ),
        ),

        property_description=(
            "Electronic energy of H2 "
            "in Jordan-Wigner encoding"
        ),

        tolerance=1e-10,
    )


print(
    "build_h2_case loaded successfully."
)


# COMPLETE SKW HYPERCUBE CONSTRUCTOR
# SKW CASE SEMANTIC CRITERION

# SKW CASE SEMANTIC CRITERION

"""### 3.4 SKW coin-position space criterion

"""


def skw_state_space_criterion(
    name: str,
    expected_dim: int,
    description: str = "",
) -> SemanticCriterion:
    'Check that every SKW coalition yields a normalized state vector in the same coin-position Hilbert space.'

    expected_dim = int(expected_dim)

    def evaluator(
        state: Array,
        state_kind: str,
        coalition: frozenset[str],
        expected: complex,
        tolerance: float,
    ) -> tuple[bool, float, str]:

        del coalition, expected

        state = np.asarray(
            state,
            dtype=complex
        )

        # SKW is represented using state vectors.
        representation_ok = (
            state_kind == "statevector"
            and state.ndim == 1
        )

        # All coalitions must remain
        # in the same coin-position space.
        dimension_ok = (
            representation_ok
            and state.shape[0] == expected_dim
        )

        # Normalization check.
        if representation_ok:
            norm = float(
                np.real(
                    np.vdot(
                        state,
                        state
                    )
                )
            )
        else:
            norm = np.nan

        normalized_ok = (
            representation_ok
            and abs(norm - 1.0) <= tolerance
        )

        passed = (
            dimension_ok
            and normalized_ok
        )

        detail = (
            f"dimension="
            f"{state.shape[0] if state.ndim == 1 else 'invalida'}, "
            f"dimension_esperada={expected_dim}, "
            f"norma={norm:.12f}, "
            f"dimension_ok={dimension_ok}, "
            f"normalizacion_ok={normalized_ok}"
        )

        return (
            passed,
            norm,
            detail
        )

    return SemanticCriterion(
        name=name,
        evaluator=evaluator,
        description=description,
    )


# COMPLETE SKW HYPERCUBE CONSTRUCTOR

"""### 3.5 SKW on the hypercube

"""

def build_skw_case(
    n=8,
    marked_vertex=0,
    time_steps=19,
    gamma=1.0,
):
    'Build the SKW QSMEF case following the experimental configuration.\n\nFirst evolve the original walk to the chosen time, then evaluate single-step coalition interventions on the resulting prior state.'

    import numpy as np

    N = 2 ** n
    dim = n * N

    # ORIGINAL UNIFORM STATE

    psi_uniform = np.ones(
        dim,
        dtype=complex
    ) / np.sqrt(dim)

    # ORACLE

    def apply_oracle(state):

        amplitudes = state.reshape(
            n,
            N
        ).copy()

        amplitudes[
            :,
            marked_vertex
        ] *= -1.0

        return amplitudes.reshape(-1)

    # GROVER COIN

    G_coin = (
        2.0
        * np.ones(
            (n, n),
            dtype=complex
        )
        / n
        - np.eye(
            n,
            dtype=complex
        )
    )

    def apply_grover(state):

        amplitudes = state.reshape(
            n,
            N
        )

        result = (
            G_coin
            @ amplitudes
        )

        return result.reshape(-1)

    # CONDITIONAL SHIFT

    def apply_shift(state):

        amplitudes = state.reshape(
            n,
            N
        )

        output = np.zeros_like(
            amplitudes
        )

        for c in range(n):

            bit_mask = (
                1
                << c
            )

            for x in range(N):

                destination = (
                    x ^ bit_mask
                )

                output[
                    c,
                    destination
                ] = amplitudes[
                    c,
                    x
                ]

        return output.reshape(-1)

    # CONSTRUCTION OF STATE psi_t

    psi_t = psi_uniform.copy()

    for _ in range(time_steps):

        psi_t = apply_oracle(
            psi_t
        )

        psi_t = apply_grover(
            psi_t
        )

        psi_t = apply_shift(
            psi_t
        )

    # ENERGY OBSERVABLE
    #
    # H = I_C ⊗ (-gamma A_P - |w><w|)

    def skw_observable(
        state,
        state_kind=None
    ):

        amplitudes = state.reshape(
            n,
            N
        )

        adjacency_expectation = (
            0.0 + 0.0j
        )

        for coin in range(n):

            vector = amplitudes[
                coin
            ]

            for bit in range(n):

                mask = (
                    1
                    << bit
                )

                permuted = np.array([
                    x ^ mask
                    for x in range(N)
                ])

                adjacency_expectation += (
                    np.vdot(
                        vector,
                        vector[permuted]
                    )
                )

        marked_probability = np.sum(
            np.abs(
                amplitudes[
                    :,
                    marked_vertex
                ]
            ) ** 2
        )

        value = (
            -gamma
            * adjacency_expectation
            - marked_probability
        )

        return float(
            np.real_if_close(
                value
            )
        )

    # QSMEF OPERATIONS / PLAYERS

    O = OperationSpec(
        action=apply_oracle,
        declared_unitary=True,
        unitarity_rationale=(
            "The oracle is a phase reflection "
            "about the marked vertex."
        ),
    )

    G = OperationSpec(
        action=apply_grover,
        declared_unitary=True,
        unitarity_rationale=(
            "The Grover coin is a unitary operator "
            "on the coin space."
        ),
    )

    S = OperationSpec(
        action=apply_shift,
        declared_unitary=True,
        unitarity_rationale=(
            "The shift is a reversible permutation "
            "on coin-position states."
        ),
    )

    # QSMEF GAME SCHEDULE
    #
    # Each coalition acts ONLY ONCE on psi_t.

    schedule = [
        "O",
        "G",
        "S",
    ]

    # DESCRIPTIVE INFORMATION

    print()
    print('Case configuration: SKW - Hipercubo')
    print("-" * 72)

    print(f"n = {n}")
    print(f"N = {N}")
    print(f"Vértice marcado: {marked_vertex}")
    print(f"Instante evaluado t = {time_steps}")
    print(f"gamma = {gamma}")

    print()
    print("Espacio de estados:")
    print(f"  Espacio de moneda: dimensión {n}")
    print(f"  Espacio de posición: dimensión {N}")
    print(f"  Dimensión total: {dim} = n * N")

    print()
    print('State preparation:')
    print("  The initial state is a uniform superposition.")
    print(
        f"  Se ejecutan {time_steps} pasos SKW completos O -> G -> S."
    )
    print(
        f"  QSMEF recibe como estado inicial del juego el estado psi_{time_steps}."
    )

    print()
    print("QSMEF players:")
    print("  {O, G, S}")

    print()
    print("Sequence evaluated by QSMEF:")
    print("  O -> G -> S")
    print("  The schedule contains 3 operations.")
    print("  Each coalition is applied once to psi_t.")

    print()
    print('Energy-like observable:')
    print("  H = I_C ⊗ (-gamma A_P - |w><w|)")

    print()
    print('Characteristic game:')
    print("  v_t(C) = M_H(U_C psi_t) - M_H(psi_t)")

    print()
    print("Coaliciones QSMEF:")
    print(
        "  {}, {O}, {G}, {S}, {O,G}, {O,S}, {G,S}, {O,G,S}"
    )

    print("-" * 72)

    # QSMEF CASE CONSTRUCTION

    return QSMEFCase(

        name=(
            f"SKW hipercubo "
            f"n={n}, t={time_steps}"
        ),

        initial_state=psi_t,

        operations={
            "O": O,
            "G": G,
            "S": S,
        },

        players=[
            "O",
            "G",
            "S",
        ],

        schedule=schedule,

        observable=skw_observable,

        constraints=(),

        semantic_contract=SemanticContract(

            description=(
                "All SKW coalitions act "
                "on the same psi_t state and must remain "
                "in the same coin-position space. "
                "They must also produce normalized states "
                "and be evaluated using the same "
                "energy observable. The interval criterion is used "
                "as a supplementary numerical check "
                "del observable."
            ),

            criteria=(

                skw_state_space_criterion(
                    name=(
                        'Preservation of the coin-position space'
                    ),
                    expected_dim=dim,
                    description=(
                        "Checks that every coalition produces "
                        "a normalized state vector "
                        "in the same space "
                        "moneda-posicion del paseo SKW."
                    ),
                ),

                semantic_interval_criterion(
                    name=(
                        "Rango espectral del observable SKW"
                    ),
                    lower=-float(
                        abs(gamma) * n + 1
                    ),
                    upper=float(
                        abs(gamma) * n + 1
                    ),
                    description=(
                        "Checks that the expectation of the "
                        "observable permanezca dentro de una "
                        "bound consistent with "
                        "-gamma*A-|w><w| on the hypercube "
                        "n-dimensional."
                    ),
                ),
            ),
        ),

        property_description=(
            "Change in the expectation of the energy observable "
            f"en el paso funcional evaluado desde psi_{time_steps}"
        ),

        tolerance=1e-10,
    )


print(
    "build_skw_case loaded successfully."
)

# COMPLETE QPE-SHOR CONSTRUCTOR

"""### 3.6 QPE de Shor

"""

def build_qpe_shor_case(
    N=21,
    a=2,
    counting_qubits=5,
):

    import numpy as np

    m = counting_qubits

    # Number of qubits needed to represent 0,...,N-1
    work_qubits = int(
        np.ceil(
            np.log2(N)
        )
    )

    work_dim = 2 ** work_qubits

    total_qubits = (
        m + work_qubits
    )

    dim = 2 ** total_qubits


    # INITIAL STATE
    #
    # |0...0> |1>

    psi0_qpe = np.zeros(
        dim,
        dtype=complex
    )

    psi0_qpe[0] = 1.0


    def prepare_work(state):
        # X permutation on the least significant bit of the work register.
        # It is unitary over the full Hilbert space, not only on |0>.
        return state[np.arange(dim) ^ 1]

    # HADAMARD MATRIX

    H1_local = (
        np.array([
            [1, 1],
            [1, -1]
        ], dtype=complex)
        / np.sqrt(2)
    )

    I2_local = np.eye(
        2,
        dtype=complex
    )


    def kron_local(operators):

        result = np.array(
            [[1.0 + 0.0j]]
        )

        for operator in operators:
            result = np.kron(
                result,
                operator
            )

        return result


    # COUNTING REGISTER PREPARATION
    #
    # H^⊗m ⊗ I

    Hprep_matrix = kron_local(
        [H1_local] * m
        +
        [I2_local] * work_qubits
    )


    def apply_hprep(state):

        return (
            Hprep_matrix
            @ state
        )


    # CONTROLLED MODULAR MULTIPLICATION
    #
    # |y> -> |a^(2^k) y mod N>
    #
    # when control qubit k is 1.

    def make_controlled_modular_multiplication(k):

        multiplier = pow(
            a,
            2 ** k,
            N
        )

        # q0 is the most significant qubit
        control_mask = (
            1
            << k
        )


        def apply_controlled_modular_multiplication(
            state
        ):

            output = np.zeros_like(
                state
            )


            for index, amplitude in enumerate(
                state
            ):

                counting_value = (
                    index
                    >> work_qubits
                )

                work_value = (
                    index
                    & (work_dim - 1)
                )


                control_is_one = (
                    counting_value
                    & control_mask
                ) != 0


                if (
                    control_is_one
                    and work_value < N
                ):

                    new_work_value = (
                        multiplier
                        * work_value
                    ) % N

                else:

                    new_work_value = (
                        work_value
                    )


                new_index = (
                    counting_value
                    << work_qubits
                ) | new_work_value


                output[
                    new_index
                ] += amplitude


            return output


        return (
            apply_controlled_modular_multiplication
        )


    # INVERSE QFT ON THE COUNTING REGISTER

    size_count = 2 ** m

    row = np.arange(
        size_count
    )[:, None]

    column = np.arange(
        size_count
    )[None, :]


    IQFT_matrix = (
        np.exp(
            -2j
            * np.pi
            * row
            * column
            / size_count
        )
        / np.sqrt(size_count)
    )


    def apply_iqft(state):

        amplitudes = state.reshape(
            size_count,
            work_dim
        )

        result = (
            IQFT_matrix
            @ amplitudes
        )

        return result.reshape(-1)


    # Observable H_per: projector onto counting outcomes associated
    # with estimates close to fractions j/r, for r=6.
    # The exact set must be checked against the original experiment.
    order = 6
    selected_outcomes = {5, 6, 10, 11, 16, 21, 22, 26, 27}

    def qpe_observable(state, state_kind=None):
        amplitudes = state.reshape(size_count, work_dim)
        return float(np.sum(np.abs(amplitudes[list(selected_outcomes), :]) ** 2))

    operations = {
        "B0": OperationSpec(action=prepare_work, declared_unitary=True,
            unitarity_rationale="X on the least significant bit of the work register."),
        "B1": OperationSpec(action=apply_hprep, declared_unitary=True,
            unitarity_rationale="Hadamard on the counting register."),
        "IQFT": OperationSpec(action=apply_iqft, declared_unitary=True,
            unitarity_rationale="Transformada inversa de Fourier."),
    }
    players = ["B0", "B1"]
    for k in range(m):
        operation_name = f"B2_{k}"
        operations[operation_name] = OperationSpec(
            action=make_controlled_modular_multiplication(k),
            declared_unitary=True,
            unitarity_rationale=f"Multiplicación modular controlada por a^(2^{k}) mod N.",
        )
        players.append(operation_name)
    schedule = players + ["IQFT"]

    # QSMEF CASE
    #
    # IMPORTANT:
    #
    # The rejection is SEMANTIC.
    # The circuit may be mathematically valid, but
    # partial coalitions do not necessarily preserve
    # the same interpretation of phase estimation.

    from fractions import Fraction
    def convergents(frac):
        n, d = frac.numerator, frac.denominator
        cf = []
        while d:
            q, rem = divmod(n, d)
            cf.append(q)
            n, d = d, rem
        p0, p1, q0, q1 = 0, 1, 1, 0
        for term in cf:
            p0, p1 = p1, term * p1 + p0
            q0, q1 = q1, term * q1 + q0
            yield Fraction(p1, q1)

    def recovered_period(x):
        for fraction in convergents(Fraction(int(x), size_count)):
            candidate = fraction.denominator
            if (1 < candidate < N and pow(a, candidate, N) == 1
                    and all(pow(a, d, N) != 1 for d in range(1, candidate))):
                return candidate == order
        return False

    successful_outcomes = [x for x in range(size_count) if recovered_period(x)]

    def compare_period_probabilities(state, state_kind, coalition, expected, tolerance):
        del state_kind, coalition
        amplitudes = state.reshape(size_count, work_dim)
        p_recovery = float(np.sum(np.abs(amplitudes[successful_outcomes, :]) ** 2))
        residual = abs(float(expected.real) - p_recovery)
        return residual <= tolerance, p_recovery, f"p_observable={expected.real:.6f}; p_recovery={p_recovery:.6f}; diferencia={residual:.6f}"

    qpe_semantic_criterion = SemanticCriterion(
        name='Correspondence between observable and period recovery',
        evaluator=compare_period_probabilities,
        description="Compares the projector expectation with period recovery using continued fractions and modular verification.",
    )

    print(f"QPE/Shor: N={N}, a={a}, conteo={m}, trabajo={work_qubits}; jugadores={players}")
    print(f"Resultados proyectados: {sorted(selected_outcomes)}; resultados recuperables: {successful_outcomes}")

    return QSMEFCase(

        name=(
            f"QPE-Shor "
            f"N={N}, a={a}, m={m}"
        ),

        initial_state=psi0_qpe,

        operations=operations,

        players=players,

        schedule=schedule,

        observable=qpe_observable,

        constraints=(),

        semantic_contract=SemanticContract(

            description=(
                "The observable probability must agree with classical period recovery."
            ),

            criteria=(qpe_semantic_criterion,),
        ),

        property_description=(
            "Projected probability of counting outcomes associated with the period"
        ),

        tolerance=1e-10,
    )


print(
    "build_qpe_shor_case loaded successfully."
)


"""## 4. Computing Shapley contributions

"""


def compute_shapley_values(
    case: QSMEFCase,
    validation_result: dict[str, Any],
    show_table: bool = True,
) -> dict[str, Any]:
    'Compute Shapley contributions for a QSMEF case.\n\nCompute contributions only if the case was classified as applicable.'

    # Applicability check

    if validation_result["verdict"] != "APPLICABLE":

        print("\n" + "-" * 76)
        print("SHAPLEY CONTRIBUTIONS")
        print("-" * 76)

        print(
            'Contributions are not computed because the case was not classified as APPLICABLE.'
        )

        return {
            "computed": False,
            "reason": (
                "The case does not satisfy all "
                "QSMEF applicability conditions."
            ),
            "shapley_values": {},
            "table": pd.DataFrame(),
            "efficiency_ok": None,
            "efficiency_residual": None,
        }


    # Case data

    players = list(case.players)

    n = len(players)

    coalitions_df = validation_result[
        "coalitions"
    ].copy()


    # Convert coalition labels to sets

    coalition_values = {}

    for _, row in coalitions_df.iterrows():

        label = row["coalición"]

        if label == "∅":
            coalition = frozenset()

        else:
            content = (
                label
                .replace("{", "")
                .replace("}", "")
                .strip()
            )

            coalition = frozenset(
                item.strip()
                for item in content.split(",")
                if item.strip()
            )

        coalition_values[
            coalition
        ] = float(
            row["v(C)"]
        )


    # Shapley formula

    shapley_values = {}

    for player in players:

        phi = 0.0

        other_players = [
            p
            for p in players
            if p != player
        ]

        for size in range(
            len(other_players) + 1
        ):

            for subset_tuple in itertools.combinations(
                other_players,
                size,
            ):

                S = frozenset(
                    subset_tuple
                )

                S_with_player = frozenset(
                    set(S) | {player}
                )

                weight = (
                    math.factorial(len(S))
                    * math.factorial(
                        n - len(S) - 1
                    )
                    / math.factorial(n)
                )

                marginal_contribution = (
                    coalition_values[
                        S_with_player
                    ]
                    - coalition_values[
                        S
                    ]
                )

                phi += (
                    weight
                    * marginal_contribution
                )

        shapley_values[
            player
        ] = float(phi)


    # Efficiency axiom check

    grand_coalition = frozenset(
        players
    )

    v_grand = coalition_values[
        grand_coalition
    ]

    shapley_sum = sum(
        shapley_values.values()
    )

    efficiency_residual = abs(
        shapley_sum - v_grand
    )

    efficiency_ok = (
        efficiency_residual
        <= case.tolerance
    )


    # Results table

    shapley_df = pd.DataFrame(
        [
            {
                "jugador": player,
                "phi": shapley_values[
                    player
                ],
            }
            for player in players
        ]
    )


    # Output

    print("\n" + "-" * 76)
    print("SHAPLEY CONTRIBUTIONS")
    print("-" * 76)

    print(
        f"v(B) = {v_grand:.12f}"
    )

    print(
        f"Σ phi_i = {shapley_sum:.12f}"
    )

    print(
        "Efficiency residual = "
        f"{efficiency_residual:.3e}"
    )

    print(
        "Eficiencia: "
        + (
            "OK"
            if efficiency_ok
            else "NO CUMPLIDA"
        )
    )

    if show_table:

        display(
            shapley_df
        )


    return {
        "computed": True,
        "shapley_values":
            shapley_values,
        "table":
            shapley_df,
        "v_grand":
            v_grand,
        "shapley_sum":
            shapley_sum,
        "efficiency_ok":
            efficiency_ok,
        "efficiency_residual":
            efficiency_residual,
    }

"""## 5. Semi-automatic granularity assistant

The constructor provides atomic blocks. The assistant generates contiguous partitions, preserves operation order and fixed operations, enforces the $2^L$ budget, and uses semantic validation to rank only candidates compatible with the declared scope.

"""

"""Explainable semi-automatic granularity assistant for QSMEF.

Load AFTER the cells defining OperationSpec, SemanticCriterion, SemanticContract, QSMEFCase, and validate_qsmef_case.

The assistant does not invent the scientific question. Given a question, functional metadata, and a coalition budget:

1. infer which roles should be distinguished;
2. generate contiguous circuit partitions;
3. discard partitions incompatible with the question or budget;
4. construct grouped QSMEF cases without changing order;
5. run the existing QSMEF validator;
6. return a ranking and justification for each recommendation.
"""


from dataclasses import dataclass, field
from itertools import product
from math import log2
from typing import Any, Mapping, Optional, Sequence
import contextlib
import io
import re
import unicodedata

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BlockMetadata:
    'Functional description of an identified atomic player.'

    name: str
    role: str
    description: str = ""
    keywords: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class GranularityObjective:
    'Declared scope for granularity selection.'

    question: str
    distinguish_roles: Sequence[str] = field(default_factory=tuple)
    required_roles: Sequence[str] = field(default_factory=tuple)
    max_coalitions: int = 1024
    max_candidates: int = 4096
    validate_semantics: bool = True


@dataclass(frozen=True)
class GranularityCandidate:
    'Candidate partition represented as groups of atomic players.'

    groups: tuple[tuple[str, ...], ...]

    @property
    def player_count(self) -> int:
        return len(self.groups)

    @property
    def coalition_count(self) -> int:
        return 2 ** self.player_count

    @property
    def label(self) -> str:
        return " | ".join("+".join(group) for group in self.groups)


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def infer_distinguished_roles(
    question: str,
    metadata: Mapping[str, BlockMetadata],
) -> tuple[str, ...]:
    'Infer roles mentioned in the research question from explainable metadata.\n\nUse transparent keyword matching rather than an opaque model.'

    normalized_question = f" {_normalize_text(question)} "
    detected: list[str] = []
    for item in metadata.values():
        terms = (item.role, *item.keywords)
        if any(
            f" {_normalize_text(term)} " in normalized_question
            for term in terms
            if _normalize_text(term)
        ):
            if item.role not in detected:
                detected.append(item.role)
    return tuple(detected)


def objective_from_question(
    question: str,
    metadata: Mapping[str, BlockMetadata],
    *,
    max_coalitions: int = 1024,
    required_roles: Sequence[str] = (),
    distinguish_roles: Optional[Sequence[str]] = None,
    max_candidates: int = 4096,
    validate_semantics: bool = True,
) -> GranularityObjective:
    'Build the objective and infer roles when they are not explicitly provided.'

    inferred = infer_distinguished_roles(question, metadata)
    roles = tuple(distinguish_roles) if distinguish_roles is not None else inferred
    return GranularityObjective(
        question=question,
        distinguish_roles=roles,
        required_roles=tuple(required_roles),
        max_coalitions=max_coalitions,
        max_candidates=max_candidates,
        validate_semantics=validate_semantics,
    )


def _ordered_players(case: Any) -> tuple[str, ...]:
    """Return ordered players and require one occurrence per player."""

    players = tuple(str(p) for p in case.players)
    schedule = tuple(str(op) for op in case.schedule)
    missing = [p for p in players if p not in schedule]
    repeated = [p for p in players if schedule.count(p) != 1]
    if missing:
        raise ValueError(f"Jugadores ausentes del schedule: {missing}")
    if repeated:
        raise ValueError(
            "Automatic generation requires one occurrence per player. "
            f"Jugadores problemáticos: {repeated}. Despliegue primero las "
            "occurrences as distinct atomic blocks."
        )
    return tuple(op for op in schedule if op in set(players))


def _can_join_in_schedule(case: Any, left: str, right: str) -> bool:
    """Merge adjacent players only; never skip a fixed operation."""

    schedule = tuple(str(op) for op in case.schedule)
    return schedule.index(right) == schedule.index(left) + 1


def generate_contiguous_candidates(
    case: Any,
    *,
    max_candidates: int = 4096,
) -> list[GranularityCandidate]:
    'Generate contiguous partitions, from finest to coarsest.'

    ordered = _ordered_players(case)
    if not ordered:
        raise ValueError("The case has no players.")

    optional_boundaries = [
        i for i in range(len(ordered) - 1)
        if _can_join_in_schedule(case, ordered[i], ordered[i + 1])
    ]
    forced_boundaries = set(range(len(ordered) - 1)) - set(optional_boundaries)
    total = 2 ** len(optional_boundaries)
    if total > max_candidates:
        raise ValueError(
            f"Se generarían {total} particiones. Aumente max_candidates o "
            "declare previamente bloques de mayor nivel."
        )

    candidates: list[GranularityCandidate] = []
    for choices in product((False, True), repeat=len(optional_boundaries)):
        cuts = set(forced_boundaries)
        cuts.update(
            boundary
            for boundary, cut in zip(optional_boundaries, choices)
            if cut
        )
        groups: list[tuple[str, ...]] = []
        start = 0
        for i in range(len(ordered) - 1):
            if i in cuts:
                groups.append(tuple(ordered[start:i + 1]))
                start = i + 1
        groups.append(tuple(ordered[start:]))
        candidates.append(GranularityCandidate(tuple(groups)))

    return sorted(candidates, key=lambda c: (-c.player_count, c.label))


def _roles_of_group(
    group: Sequence[str], metadata: Mapping[str, BlockMetadata]
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(metadata[name].role for name in group))


def _candidate_filters(
    candidate: GranularityCandidate,
    metadata: Mapping[str, BlockMetadata],
    objective: GranularityObjective,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if candidate.coalition_count > objective.max_coalitions:
        reasons.append(
            f"costo {candidate.coalition_count} > presupuesto "
            f"{objective.max_coalitions}"
        )

    available_roles = {
        metadata[name].role for group in candidate.groups for name in group
    }
    missing = set(objective.required_roles) - available_roles
    if missing:
        reasons.append(f"faltan roles requeridos: {sorted(missing)}")

    separated = set(objective.distinguish_roles)
    for group in candidate.groups:
        mixed = set(_roles_of_group(group, metadata)) & separated
        if len(mixed) > 1:
            reasons.append(
                f"el grupo {'+'.join(group)} mezcla roles que la pregunta "
                f"debe distinguir: {sorted(mixed)}"
            )
    return not reasons, reasons


def _adapt_semantic_contract(original_contract: Any, group_map: Mapping[str, tuple[str, ...]]) -> Any:
    'Expand grouped coalitions before evaluating the original semantic criteria.'

    if original_contract is None or not getattr(original_contract, "criteria", ()):
        return original_contract

    adapted = []
    for criterion in original_contract.criteria:
        original_evaluator = criterion.evaluator

        def evaluator(state, state_kind, coalition, expected, tolerance,
                      _original=original_evaluator):
            expanded = frozenset(
                atomic
                for grouped in coalition
                for atomic in group_map.get(grouped, (grouped,))
            )
            return _original(state, state_kind, expanded, expected, tolerance)

        adapted.append(
            SemanticCriterion(
                name=criterion.name,
                evaluator=evaluator,
                description=criterion.description,
            )
        )
    return SemanticContract(
        description=original_contract.description,
        criteria=tuple(adapted),
    )

def build_grouped_case(
    original_case: Any,
    candidate: GranularityCandidate,
    *,
    name: Optional[str] = None,
) -> Any:
    'Build a grouped QSMEFCase and correctly rewrite the execution schedule.'

    normalized = _normalize_operations(original_case.operations)
    group_names: list[str] = []
    group_map: dict[str, tuple[str, ...]] = {}
    atomic_to_group: dict[str, str] = {}
    new_operations = {
        op_name: op
        for op_name, op in normalized.items()
        if op_name not in set(original_case.players)
    }

    for number, group in enumerate(candidate.groups, start=1):
        proposed = "+".join(group)
        group_name = proposed if proposed not in new_operations else f"G{number}_{proposed}"
        group_names.append(group_name)
        group_map[group_name] = tuple(group)
        atomic_to_group.update({atomic: group_name for atomic in group})
        specs = tuple(normalized[atomic] for atomic in group)

        if all(spec.is_matrix() for spec in specs):
            matrices = tuple(np.asarray(spec.action, dtype=complex) for spec in specs)
            composed = np.eye(matrices[0].shape[0], dtype=complex)
            for matrix in matrices:
                composed = matrix @ composed
            new_operations[group_name] = OperationSpec(action=composed)
        else:
            declared = all(bool(spec.declared_unitary) for spec in specs)

            # OperationSpec.apply calls functional actions with one
            # argument and supports only state vectors in that case.
            def apply_group(state, _specs=specs):
                result = state
                for spec in _specs:
                    result = spec.apply(result, "statevector")
                return result

            new_operations[group_name] = OperationSpec(
                action=apply_group,
                declared_unitary=declared,
                unitarity_rationale=(
                    "Ordered composition of declared unitary operations"
                    if declared else ""
                ),
            )

    new_schedule: list[str] = []
    emitted: set[str] = set()
    for operation in map(str, original_case.schedule):
        if operation not in atomic_to_group:
            new_schedule.append(operation)
            continue
        grouped = atomic_to_group[operation]
        if grouped not in emitted:
            new_schedule.append(grouped)
            emitted.add(grouped)

    contract = _adapt_semantic_contract(original_case.semantic_contract, group_map)
    return QSMEFCase(
        name=name or f"{original_case.name} | granularidad: {candidate.label}",
        initial_state=original_case.initial_state,
        operations=new_operations,
        players=tuple(group_names),
        schedule=tuple(new_schedule),
        observable=original_case.observable,
        constraints=original_case.constraints,
        semantic_contract=contract,
        property_description=original_case.property_description,
        tolerance=original_case.tolerance,
    )


def _interpretability(candidate: GranularityCandidate, metadata: Mapping[str, BlockMetadata]) -> float:
    """Reward functionally homogeneous groups."""

    scores = []
    for group in candidate.groups:
        roles = [metadata[name].role for name in group]
        dominant = max(roles.count(role) for role in set(roles))
        scores.append(dominant / len(roles))
    return float(np.mean(scores))


def recommend_granularity(
    case: Any,
    metadata: Mapping[str, BlockMetadata],
    objective: GranularityObjective,
    *,
    show_table: bool = True,
) -> dict[str, Any]:
    'Generate, validate, and rank candidate granularities.\n\nPrioritize QSMEF applicability, alignment with the research question, interpretability, and computational cost.'

    players = set(map(str, case.players))
    missing_metadata = players - set(metadata)
    if missing_metadata:
        raise ValueError(f"Faltan metadatos para: {sorted(missing_metadata)}")
    if objective.max_coalitions < 2:
        raise ValueError("max_coalitions must be at least 2.")

    candidates = generate_contiguous_candidates(
        case, max_candidates=objective.max_candidates
    )
    rows: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    max_players_budget = max(1.0, log2(objective.max_coalitions))

    for candidate in candidates:
        structurally_valid, reasons = _candidate_filters(
            candidate, metadata, objective
        )
        entry: dict[str, Any] = {
            "candidate": candidate,
            "case": None,
            "validation": None,
            "accepted": False,
            "reasons": list(reasons),
        }
        if structurally_valid:
            grouped_case = build_grouped_case(case, candidate)
            # The original validator prints a report even when
            # tables are hidden. Capture this output during ranking
            # to avoid flooding the notebook for every candidate.
            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                validation = validate_qsmef_case(grouped_case, show_tables=False)
            applicable = validation["verdict"] == "APPLICABLE"
            if objective.validate_semantics and not applicable:
                entry["reasons"].append(validation["reason"])
            else:
                entry["accepted"] = True
            entry["case"] = grouped_case
            entry["validation"] = validation

        interpretability = _interpretability(candidate, metadata)
        cost_score = max(0.0, 1.0 - candidate.player_count / max_players_budget)
        # Applicability takes priority, followed by interpretability and cost.
        score = (
            (100.0 if entry["accepted"] else 0.0)
            + 10.0 * interpretability
            + 5.0 * cost_score
        )
        entry["score"] = score
        rows.append({
            "Granularidad": candidate.label,
            "Jugadores": candidate.player_count,
            "Coaliciones": candidate.coalition_count,
            "Interpretabilidad": round(interpretability, 3),
            "Veredicto": (
                entry["validation"]["verdict"]
                if entry["validation"] is not None
                else "DESCARTADA"
            ),
            "Aceptada": entry["accepted"],
            "Puntaje": round(score, 3),
            "Justificación": "; ".join(entry["reasons"]) or "meets all criteria",
        })
        if entry["accepted"]:
            accepted.append(entry)

    accepted.sort(key=lambda item: (-item["score"], item["candidate"].player_count))
    table = pd.DataFrame(rows).sort_values(
        ["Aceptada", "Puntaje", "Jugadores"], ascending=[False, False, True]
    ).reset_index(drop=True)
    recommendation = accepted[0] if accepted else None

    if show_table:
        print("=" * 80)
        print('QSMEF GRANULARITY SELECTION ASSISTANT')
        print("=" * 80)
        print(f"Pregunta: {objective.question}")
        print(f"Roles a distinguir: {tuple(objective.distinguish_roles) or 'not inferred'}")
        print(f"Presupuesto: {objective.max_coalitions} coaliciones")
        display(table)
        if recommendation:
            print(f"\nRECOMENDACIÓN: {recommendation['candidate'].label}")
            print(
                "Interpretation: granularity recommended for the question, "
                "the declared scope and budget."
            )
        else:
            print('\nNO RECOMMENDATION: no candidate meets all criteria.')

    return {
        "objective": objective,
        "recommendation": recommendation,
        "accepted": accepted,
        "all_results": rows,
        "table": table,
    }


def example_maxcut_granularity(case: Any) -> dict[str, Any]:
    'Example using the C1-M1-C2-M2 case defined in this file.'

    metadata = {
        "C1": BlockMetadata("C1", "costo", keywords=("cost", "coste")),
        "M1": BlockMetadata("M1", "mezcla", keywords=("mixer", "mixing")),
        "C2": BlockMetadata("C2", "costo", keywords=("cost", "coste")),
        "M2": BlockMetadata("M2", "mezcla", keywords=("mixer", "mixing")),
    }
    objective = objective_from_question(
        "How do the cost and mixer blocks at each layer contribute?",
        metadata,
        max_coalitions=64,
        required_roles=("costo", "mezcla"),
    )
    return recommend_granularity(case, metadata, objective)


print("QSMEF semi-automatic granularity assistant loaded successfully.")

"""## 6. Orquestador del pipeline QSMEF

"""


# GRANULARITY REQUESTS FOR DOCUMENTED CASES

def build_granularity_request(case_key: str):
    'Return metadata and an objective for documented cases.\n\nOther cases retain their declared granularity.'

    if case_key == "maxcut":
        metadata = {
            "C1": BlockMetadata("C1", "costo", keywords=("cost", "coste")),
            "B1": BlockMetadata("B1", "mezcla", keywords=("mixer", "mixing", "mezclador")),
            "C2": BlockMetadata("C2", "costo", keywords=("cost", "coste")),
            "B2": BlockMetadata("B2", "mezcla", keywords=("mixer", "mixing", "mezclador")),
        }
        objective = objective_from_question(
            "How do the cost and mixer blocks at each QAOA layer contribute?",
            metadata,
            required_roles=("costo", "mezcla"),
            max_coalitions=16,
        )
        return metadata, objective

    if case_key == "h2":
        metadata = {
            "R0": BlockMetadata("R0", "rotación", keywords=("rotation", "rotacion", "rotaciones")),
            "E0": BlockMetadata("E0", "entrelazamiento", keywords=("entanglement", "entangler")),
            "R1": BlockMetadata("R1", "rotación", keywords=("rotation", "rotacion", "rotaciones")),
            "E1": BlockMetadata("E1", "entrelazamiento", keywords=("entanglement", "entangler")),
            "R2": BlockMetadata("R2", "rotación", keywords=("rotation", "rotacion", "rotaciones")),
        }
        objective = objective_from_question(
            "How do the rotation and entangling layers contribute to the change in H2 electronic energy?",
            metadata,
            required_roles=("rotación", "entrelazamiento"),
            max_coalitions=32,
        )
        return metadata, objective

    if case_key == "skw":
        metadata = {
            "O": BlockMetadata("O", "oráculo", keywords=("oracle", "marcado")),
            "G": BlockMetadata("G", "moneda", keywords=("coin", "grover")),
            "S": BlockMetadata("S", "desplazamiento", keywords=("shift", "flip-flop")),
        }
        objective = objective_from_question(
            "How do the oracle, Grover coin, and flip-flop shift contribute to the change in the energy observable in one step of SKW?",
            metadata,
            required_roles=("oráculo", "moneda", "desplazamiento"),
            max_coalitions=8,
        )
        return metadata, objective

    return None


# REGISTERED CONSTRUCTORS

def build_case_registry():
    """Build the five journal cases using declared granularities."""

    return {
        "maxcut": ("QAOA-MaxCut C6", build_maxcut_case()),
        "h2": ("TwoLocal-H2", build_h2_case()),
        "skw": (
            "SKW hypercube",
            build_skw_case(n=8, marked_vertex=0, time_steps=19, gamma=1.0),
        ),
        "qpe": (
            "QPE-Shor",
            build_qpe_shor_case(N=21, a=2, counting_qubits=5),
        ),
        "partitioning": (
            "Graph Partitioning (Min Bisection)",
            build_graph_partitioning_case(n=6),
        ),
    }


# UNIVERSAL SINGLE-CASE PIPELINE

def run_qsmef_case(
    case_key: str,
    label: str,
    base_case: QSMEFCase,
    *,
    use_granularity_assistant: bool = False,
    show_granularity_table: bool = False,
    show_validation_tables: bool = False,
    show_shapley_table: bool = True,
):
    'Validate one case using its declared granularity.\n\nOptionally use the granularity assistant. Compute Shapley contributions only for applicable cases.'

    selected_case = base_case
    granularity_result = None
    selection_status = "DECLARED GRANULARITY"

    request = build_granularity_request(case_key)
    if use_granularity_assistant and request is not None:
        metadata, objective = request
        granularity_result = recommend_granularity(
            base_case,
            metadata,
            objective,
            show_table=show_granularity_table,
        )
        recommendation = granularity_result["recommendation"]
        if recommendation is not None:
            selected_case = recommendation["case"]
            selection_status = "RECOMMENDED"
        else:
            # Keep the declared case to explain why it is not
            # admissible; do not present it as an assistant recommendation.
            selection_status = "NO ADMISSIBLE CANDIDATE"

    validation = validate_qsmef_case(
        selected_case,
        show_tables=show_validation_tables,
    )

    shapley = None
    if validation["verdict"] == "APPLICABLE":
        shapley = compute_shapley_values(
            selected_case,
            validation,
            show_table=show_shapley_table,
        )
    else:
        print(
            'Shapley contributions are not computed because the configuration does not meet the declared applicability conditions.'
        )

    return {
        "key": case_key,
        "label": label,
        "base_case": base_case,
        "selected_case": selected_case,
        "selection_status": selection_status,
        "granularity": granularity_result,
        "validation": validation,
        "shapley": shapley,
    }


# MULTICASE ORCHESTRATOR

def run_qsmef_multicase(
    *,
    use_granularity_assistant: bool = True,
    show_granularity_tables: bool = False,
    show_validation_tables: bool = False,
    show_shapley_tables: bool = True,
):
    'Run the uniform multicase pipeline and return detailed results and a summary.'

    registry = build_case_registry()
    results = {}
    rows = []

    for case_key, (label, case) in registry.items():
        print("\n" + "=" * 88)
        print("CASE:", label)
        print("=" * 88)

        result = run_qsmef_case(
            case_key,
            label,
            case,
            use_granularity_assistant=use_granularity_assistant,
            show_granularity_table=show_granularity_tables,
            show_validation_tables=show_validation_tables,
            show_shapley_table=show_shapley_tables,
        )
        results[case_key] = result

        shapley_text = "No calculado"
        if result["shapley"] is not None and result["shapley"].get("computed"):
            shapley_text = " | ".join(
                f"{player}: {value:.6f}"
                for player, value in result["shapley"]["shapley_values"].items()
            )

        selected = result["selected_case"]
        rows.append({
            "Caso": label,
            "Selección": result["selection_status"],
            "Granularidad analizada": " | ".join(selected.players),
            "Jugadores": len(selected.players),
            "Coaliciones": 2 ** len(selected.players),
            "Veredicto": result["validation"]["verdict"],
            "Motivo": result["validation"]["reason"],
            "Shapley": shapley_text,
        })

    summary = pd.DataFrame(rows)
    print("\n" + "=" * 88)
    print('SUMMARY FINAL QSMEF')
    print("=" * 88)
    display(summary)

    return {
        "results": results,
        "summary": summary,
    }




"""## 7. Execution and summary

"""

# SKW variant from the article: prepare a new prior state with the modified oracle.
from dataclasses import replace

def build_skw_modified_evolution_case():
    n = 8
    N = 2**n
    phase = np.exp(1j * 0.70 * np.pi)

    # Start from the uniform state
    psi = np.ones(n * N, dtype=complex) / np.sqrt(n * N)

    # Operations for the modified implementation
    def oracle_mod(state):
        a = state.reshape(n, N).copy()
        a[:, 0] *= phase
        return a.reshape(-1)

    G = 2 * np.ones((n, n), dtype=complex) / n - np.eye(n)

    def grover(state):
        return (G @ state.reshape(n, N)).reshape(-1)

    def shift(state):
        a = state.reshape(n, N)
        out = np.zeros_like(a)
        for c in range(n):
            for x in range(N):
                out[c, x ^ (1 << c)] = a[c, x]
        return out.reshape(-1)

    # Evolve 19 steps using the modified oracle
    for _ in range(19):
        psi = oracle_mod(psi)
        psi = grover(psi)
        psi = shift(psi)

    # Keep the observable and contract from the original case
    original = build_skw_case(
        n=8, marked_vertex=0, time_steps=19, gamma=1.0
    )

    operations = dict(original.operations)
    operations["O"] = OperationSpec(
        action=oracle_mod,
        declared_unitary=True,
        unitarity_rationale="Unitary diagonal phase operator."
    )

    return replace(
        original,
        name="Modified SKW - full evolution 0.70π",
        initial_state=psi,
        operations=operations
    )


def run_journal_experiments(show_tables=False):
    'Run the five cases and the SKW modified-oracle comparison.'
    report = run_qsmef_multicase(
        use_granularity_assistant=False,
        show_granularity_tables=False,
        show_validation_tables=show_tables,
        show_shapley_tables=show_tables,
    )
    modified = build_skw_modified_evolution_case()
    modified_validation = validate_qsmef_case(modified, show_tables=show_tables)
    modified_shapley = compute_shapley_values(modified, modified_validation, show_table=show_tables)
    return {"cases": report, "skw_modified": {"validation": modified_validation, "shapley": modified_shapley}}


if __name__ == "__main__":
    run_journal_experiments(show_tables=False)
