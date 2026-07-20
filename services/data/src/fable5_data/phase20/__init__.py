"""Phase 20 deterministic Family A evaluation/holdout input register."""

from fable5_data.phase20.contracts import FamilyAEvaluationHoldoutInputRegister
from fable5_data.phase20.input_register import (
    build_family_a_evaluation_holdout_input_register,
    canonical_evaluation_holdout_input_register_bytes,
)

__all__ = [
    "FamilyAEvaluationHoldoutInputRegister",
    "build_family_a_evaluation_holdout_input_register",
    "canonical_evaluation_holdout_input_register_bytes",
]
