"""Contrato de abstração para o Repositório do Dashboard da Clínica."""

from typing import Protocol
from src.domain.dtos.clinic_summary_dto import ClinicSummaryDTO


class IClinicDashboardRepository(Protocol):
    """Interface do repositório analítico da clínica (SRP & DIP)."""

    def get_clinic_summary(self) -> ClinicSummaryDTO:
        ...
