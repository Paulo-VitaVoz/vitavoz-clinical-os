"""Contrato abstrato para operações do repositório de protocolos."""

from typing import List, Optional, Protocol
from src.domain.entities.protocol import Protocol as ProtocolEntity


class IProtocolRepository(Protocol):
    """Interface do repositório de protocolos clínicos."""

    def get_by_id(self, protocol_id: int) -> Optional[ProtocolEntity]:
        ...

    def get_by_procedure_name(self, procedure_name: str) -> Optional[ProtocolEntity]:
        ...

    def get_all(self) -> List[ProtocolEntity]:
        ...
