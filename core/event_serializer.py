"""Componente de serialização segura de eventos de domínio."""

import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Any


class EventSerializer:
    """Serializa eventos e entidades do domínio para string JSON de forma segura."""

    @staticmethod
    def _encoder(obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)

    def serialize(self, event: object) -> str:
        """Converte o objeto de evento em string JSON preservando tipos complexos.

        Args:
            event: Instância da classe do evento de domínio.

        Returns:
            str: Payload serializado em JSON.
        """
        event_dict = {
            k: v for k, v in event.__dict__.items() if not k.startswith("_")
        }
        return json.dumps(event_dict, default=self._encoder, ensure_ascii=False)