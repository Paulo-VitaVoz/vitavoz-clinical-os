"""
DTO para a Fila de Triagem da Clínica.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class PatientQueueDTO:
    """Dados consolidados para exibição na fila de triagem da clínica."""
    paciente: str
    procedimento: str
    pos_op: str
    status: str
    score: int
    alertas_clinicos: Optional[str] = None
    motivo: Optional[str] = None