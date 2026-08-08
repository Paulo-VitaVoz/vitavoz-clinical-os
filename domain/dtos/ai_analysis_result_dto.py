"""DTO contendo o resultado da extração sintomática realizada pela Inteligência Artificial."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AIAnalysisResultDTO:
    """Estrutura imutável com os dados estruturados extraídos do relato do paciente."""

    transcricao_texto: str
    dor_nivel: int
    inchaco_detectado: bool
    febre_detectada: bool
    tendencia_identificada: str
    resumo_clinico: str
    confianca_score: float
    provedor_utilizado: str
    sintomas_secundarios: List[str] = field(default_factory=list)
