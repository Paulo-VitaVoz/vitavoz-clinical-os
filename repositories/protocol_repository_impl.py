"""Implementação concreta do repositório de protocolos para SQLite/PostgreSQL."""

import json
from contextlib import closing
from typing import List, Optional
from src.database.connection import ConnectionFactory
from src.domain.entities.protocol import Protocol
from src.domain.interfaces.protocol_repository import IProtocolRepository


class ProtocolRepositoryImpl(IProtocolRepository):
    """Repositório com deserialização de regras JSON no SQLite."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def get_by_id(self, protocol_id: int) -> Optional[Protocol]:
        """Busca um protocolo por ID e deserializa o campo JSON de regras."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM protocolos WHERE id=?", (protocol_id,))
            row = c.fetchone()
            return self._map_to_entity(row) if row else None

    def get_by_procedure_name(self, procedure_name: str) -> Optional[Protocol]:
        """Busca protocolo por nome do procedimento."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM protocolos WHERE nome_procedimento=?", (procedure_name,)
            )
            row = c.fetchone()
            return self._map_to_entity(row) if row else None

    def get_all(self) -> List[Protocol]:
        """Retorna todos os protocolos cadastrados."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM protocolos")
            rows = c.fetchall()
            return [self._map_to_entity(row) for row in rows]

    def _map_to_entity(self, row) -> Protocol:
        row_dict = dict(row)
        alert_rules = (
            json.loads(row_dict["regras_json"]) if row_dict.get("regras_json") else {}
        )
        return Protocol(
            id=row_dict["id"],
            nome_procedimento=row_dict["nome_procedimento"],
            dias_acompanhamento_padrao=row_dict["dias_acompanhamento_padrao"],
            alert_rules=alert_rules,
        )
