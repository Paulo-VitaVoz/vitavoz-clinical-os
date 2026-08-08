"""Contrato abstrato para operações do repositório de pacientes."""

from typing import List, Optional, Protocol
from src.domain.dtos.patient_queue_dto import PatientQueueDTO
from src.domain.entities.patient import Patient


class IPatientRepository(Protocol):
    """Interface do repositório de pacientes baseada em Duck Typing Estático."""

    def get_joao_id(self) -> int:
        ...

    def get_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        ...

    def get_patient_by_phone(self, phone_number: str) -> Optional[Patient]:
        ...

    def get_fila_completa(self) -> List[PatientQueueDTO]:
        ...

    def update_patient_protocol(self, patient_id: int, protocol_id: int) -> bool:
        ...
