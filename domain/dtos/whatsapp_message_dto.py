"""DTO para transporte padronizado de mensagens recebidas do WhatsApp."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WhatsAppIncomingMessageDTO:
    """Estrutura imutável para desacoplamento de schemas de provedores de WhatsApp."""

    sender_phone: str
    text_content: Optional[str] = None
    audio_bytes: Optional[bytes] = None
    message_id: Optional[str] = None
