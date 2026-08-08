"""DTO contendo a consolidação de métricas financeiras e operacionais de ROI da clínica."""

from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutiveRoiDTO:
    """Objeto imutável para transporte de indicadores de ROI B2B."""

    horas_triagem_economizadas: float
    readmissoes_prevenidas: int
    economia_financeira_reais: float
    sla_medio_atendimento_minutos: float
    total_atendimentos_concluidos: int