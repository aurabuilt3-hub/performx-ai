"""Backward-compatibility shim for performx.sensorimotor."""

from performx.core import FormAlertSeverity, MovementPhase, SquatConfig
from performx.contracts import FormAlertData as FormAlert
from performx.engine import PhaseOscillator, SensorimotorEngine

__all__ = [
    "FormAlertSeverity",
    "MovementPhase",
    "SquatConfig",
    "FormAlert",
    "PhaseOscillator",
    "SensorimotorEngine",
]
