"""Contrato abstrato para operações do repositório de evoluções."""

from typing import List, Protocol
from src.domain.entities.evolution import Evolution


class IEvolutionRepository(Protocol):
    """Interface do repositório de evoluções clínicas."""

    def get_evolutions_by_patient(self, patient_id: int) -> List[Evolution]:
        ...

    def has_evolution_for_day(self, patient_id: int, dia: int) -> bool:
        ...

    def save_evolution(self, evolution: Evolution) -> None:
        ...

    def save_doctor_conduct(
        self, evolution_id: int, conduct_text: str, timestamp: str
    ) -> bool:
        ...

    def get_average_pain_by_protocol_and_day(
        self, protocol_id: int, dia: int
    ) -> float:
        ...
