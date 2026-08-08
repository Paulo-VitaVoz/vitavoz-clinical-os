"""Contrato de abstração para o Repositório de Eventos de Cuidado."""

from typing import List, Protocol
from src.domain.entities.care_event import CareEvent


class ICareEventRepository(Protocol):
    """Interface do repositório de fatos clínicos imutáveis (Care Timeline)."""

    def add_event(self, event: CareEvent) -> None:
        ...

    def get_events_by_patient(self, patient_id: int) -> List[CareEvent]:
        ...
