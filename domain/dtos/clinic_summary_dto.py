"""DTO contendo os dados consolidados do resumo executivo da clínica."""

from dataclasses import dataclass


@dataclass
class ClinicSummaryDTO:
    """Métricas operacionais agregadas para o Dashboard Executivo."""

    total_pacientes_ativos: int
    pacientes_em_alerta: int
    media_vitascore: float
    taxa_adesao_hoje: float
