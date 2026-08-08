"""Eventos de Domínio Imutáveis com Rastreabilidade Transacional."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class BaseEvent:
    """Classe base imutável para eventos com Correlation ID e Causation ID."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_on: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    )


@dataclass(frozen=True)
class EvolutionRegistered(BaseEvent):
    """Fato disparado quando uma nova evolução é registrada."""

    patient_id: int = 0
    dia: int = 0
    vitascore: int = 100
    status_alerta: str = "🟢 Normal"


@dataclass(frozen=True)
class CriticalAlertGenerated(BaseEvent):
    """Fato disparado quando o VitaScore™ atinge faixa crítica (P1/P2)."""

    patient_id: int = 0
    patient_name: str = ""
    vitascore: int = 100
    alert_status: str = "🔴 Alerta"
    alert_reason: str = ""


@dataclass(frozen=True)
class DoctorConductRegistered(BaseEvent):
    """Fato disparado quando o cirurgião prescreve conduta médica."""

    patient_id: int = 0
    evolution_id: int = 0
    conduct_text: str = ""