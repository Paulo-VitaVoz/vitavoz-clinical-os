"""Entidade de Domínio representando um registro de Evolução Clínica."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Evolution:
    """Registro diário de sintomas e avaliação clínica do paciente."""

    paciente_id: int
    dia: int
    dor: int
    inchaco: str
    febre: str
    tendencia: str
    relato: str
    score: int
    status_alerta: str
    data_registro: str
    motivo: str = "Evolução dentro do esperado para o protocolo."
    conduta_medico: Optional[str] = None
    data_conduta: Optional[str] = None
    id: Optional[int] = None
