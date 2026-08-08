"""DTO contendo a avaliação dos sintomas contra o protocolo clínico."""

from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Resultado explicável da análise clínica executada pelo protocolo."""

    alerta: bool
    status: str
    motivo: str
    score_sugerido: int
