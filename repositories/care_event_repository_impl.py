"""Implementação concreta do Repositório de Eventos de Cuidado no SQLite/PostgreSQL."""

from contextlib import closing
from typing import List
from src.database.connection import ConnectionFactory
from src.domain.entities.care_event import CareEvent
from src.domain.enums.event_type import EventType
from src.domain.interfaces.care_event_repository import ICareEventRepository


class CareEventRepository(ICareEventRepository):
    """Repositório Append-Only com desserialização defensiva para persistência de CareEvents."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def add_event(self, event: CareEvent) -> None:
        """Persiste um fato clínico imutável no banco de dados."""
        with closing(self._connection_factory()) as conn:
            with conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO care_events (
                        patient_id, event_type, timestamp, title, description, author, badge_color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        event.patient_id,
                        event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type),
                        event.timestamp,
                        event.title,
                        event.description,
                        event.author,
                        event.badge_color,
                    ),
                )

    def get_events_by_patient(self, patient_id: int) -> List[CareEvent]:
        """Retorna os eventos da linha do tempo com desserialização defensiva de EventType."""
        with closing(self._connection_factory()) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT * FROM care_events WHERE patient_id = ? ORDER BY id DESC",
                (patient_id,),
            )
            rows = c.fetchall()
            events = []
            for row in rows:
                r_dict = dict(row)
                try:
                    r_dict["event_type"] = EventType(r_dict["event_type"])
                except ValueError:
                    r_dict["event_type"] = EventType.PATIENT_RELATO
                events.append(CareEvent(**r_dict))
            return events
