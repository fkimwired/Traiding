"""Read-only external-paper shadow-readiness capability for Phase 12."""

from fable5_paper.phase12.adapters import (
    DeterministicMockPaperBrokerAdapter,
    MockReadinessScenario,
    PaperBrokerAdapter,
)
from fable5_paper.phase12.alpaca import (
    AlpacaPaperReadOnlyAdapter,
    build_alpaca_paper_read_only_adapter,
)
from fable5_paper.phase12.contracts import (
    PaperShadowReadinessArtifact,
    PaperShadowReadinessCreateRequest,
    ReadinessOutcome,
    ReadinessSourceKind,
)
from fable5_paper.phase12.workflow import PaperShadowReadinessWorkflow

__all__ = [
    "AlpacaPaperReadOnlyAdapter",
    "DeterministicMockPaperBrokerAdapter",
    "MockReadinessScenario",
    "PaperBrokerAdapter",
    "PaperShadowReadinessArtifact",
    "PaperShadowReadinessCreateRequest",
    "PaperShadowReadinessWorkflow",
    "ReadinessOutcome",
    "ReadinessSourceKind",
    "build_alpaca_paper_read_only_adapter",
]
