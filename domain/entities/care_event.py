"""Entidade de Domínio representando um Fato Clínico Imutável (Care Event)."""

from dataclasses import dataclass
from typing import Optional
from src.domain.enums.event_type import EventType


@dataclass
class CareEvent:
    """Fato clínico registrado no histórico auditável do paciente."""

    patient_id: int
    event_type: EventType
    timestamp: str
    title: str
    description: str
    author: str
    badge_color: str = "#3B82F6"
    id: Optional[int] = None
