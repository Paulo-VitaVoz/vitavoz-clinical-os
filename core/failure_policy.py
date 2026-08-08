"""Políticas de tratamento de falhas e fallback para eventos de domínio."""

import logging
from typing import Protocol
from src.core.event_serializer import EventSerializer
from src.domain.events import BaseEvent, CriticalAlertGenerated

logger = logging.getLogger(__name__)


class IFailurePolicy(Protocol):
    """Contrato para definição de políticas de tratamento de falhas em listeners."""

    def handle_exhausted_retries(
        self, listener_name: str, event: BaseEvent, exception: Exception, stacktrace: str
    ) -> None:
        """Trata o esgotamento de tentativas de execução de um ouvinte."""
        ...


class DefaultFailurePolicy(IFailurePolicy):
    """Política padrão de log estruturado para tratamento de falhas esgotadas."""

    def __init__(self, serializer: EventSerializer) -> None:
        self._serializer = serializer

    def handle_exhausted_retries(
        self, listener_name: str, event: BaseEvent, exception: Exception, stacktrace: str
    ) -> None:
        """Registra o log estruturado de erro quando todas as tentativas falham."""
        payload = self._serializer.serialize(event)
        logger.error(
            "listener_execution_failed_permanently",
            extra={
                "listener": listener_name,
                "event_id": event.event_id,
                "correlation_id": event.correlation_id,
                "error": str(exception),
                "stacktrace": stacktrace,
                "payload": payload,
            },
        )