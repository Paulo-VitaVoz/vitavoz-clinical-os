"""
Entidade de Domínio Pura: Paciente.
Representa o paciente na clínica.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Patient:
    """Modelo imutável que representa um paciente no sistema."""
    id: int
    tenant_id: str
    nome: str
    idade: int
    procedimento: str
    data_cirurgia: str
    data_retorno: str
    protocolo: str
    protocol_id: int
    alertas_clinicos: Optional[str] = None
    notas_medico: Optional[str] = None
    avatar: Optional[str] = None
    telefone: Optional[str] = None