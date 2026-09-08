"""Signal state machine (REQ-WP-007).

# @trace: REQ-WP-007
"""

from channelflow.signals.machine import IllegalTransition, SignalMachine
from channelflow.signals.models import ALLOWED, Candidate, CandidateState, Transition
from channelflow.signals.rejection import CloseBackInside, RejectionDetector

__all__ = [
    "ALLOWED",
    "Candidate",
    "CandidateState",
    "CloseBackInside",
    "IllegalTransition",
    "RejectionDetector",
    "SignalMachine",
    "Transition",
]
