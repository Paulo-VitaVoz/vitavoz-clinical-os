"""Motor de Análise Clínica e Cálculo do VitaScore™."""

from typing import List, Optional
from src.domain.dtos.evaluation_result import EvaluationResult
from src.domain.entities.protocol import Protocol
from src.domain.interfaces.protocol_repository import IProtocolRepository


class ProtocolService:
    """Aplica as regras matemáticas de desvio contra protocolos cadastrados."""

    def __init__(self, repo: IProtocolRepository) -> None:
        self._repo = repo

    def get_protocol_for_patient(self, protocol_id: int) -> Optional[Protocol]:
        """Retorna o protocolo cadastrado para o paciente."""
        return self._repo.get_by_id(protocol_id)

    def calculate_vitascore(
        self,
        protocol_id: int,
        dor: int,
        inchaco: bool,
        febre: bool,
        tendencia: str,
        sintomas_secundarios: Optional[List[str]] = None,
        confianca_score: float = 1.0,
        dia: int = 3,
    ) -> int:
        """Cálculo determinístico do índice VitaScore™ (0 a 100)."""
        if sintomas_secundarios is None:
            sintomas_secundarios = []

        protocol = self._repo.get_by_id(protocol_id)
        limite_dor = protocol.get_pain_threshold(dia) if protocol else 3

        excesso_dor = max(0, dor - limite_dor)
        penalidade_dor = excesso_dor * 12
        penalidade_sintomas = (25 if febre else 0) + (15 if inchaco else 0) + (len(sintomas_secundarios) * 10)
        penalidade_tendencia = 15 if tendencia.lower() == "piorando" else 0
        penalidade_confianca = 10 if confianca_score < 0.70 else 0

        total_penalidades = penalidade_dor + penalidade_sintomas + penalidade_tendencia + penalidade_confianca
        score_calculado = 100 - total_penalidades

        return max(0, min(100, score_calculado))

    def evaluate_symptoms_against_protocol(
        self,
        protocol_id: int,
        dor: int,
        dia: int,
        inchaco: bool = False,
        febre: bool = False,
        tendencia: str = "Estável",
        sintomas_secundarios: Optional[List[str]] = None,
        confianca_score: float = 1.0,
    ) -> EvaluationResult:
        """Avalia sintomas contra o protocolo e gera o parecer e o VitaScore™."""
        if sintomas_secundarios is None:
            sintomas_secundarios = []

        protocol = self._repo.get_by_id(protocol_id)
        limite_dor_dia = protocol.get_pain_threshold(dia) if protocol else 3

        score = self.calculate_vitascore(
            protocol_id=protocol_id,
            dor=dor,
            inchaco=inchaco,
            febre=febre,
            tendencia=tendencia,
            sintomas_secundarios=sintomas_secundarios,
            confianca_score=confianca_score,
            dia=dia,
        )

        if score < 60:
            status = "🔴 Alerta"
            alerta = True
        elif score < 85 or confianca_score < 0.70:
            status = "🟡 Atenção"
            alerta = True
        else:
            status = "🟢 Normal"
            alerta = False

        if dor > limite_dor_dia:
            motivo = f"Nível de dor ({dor}) excedeu o limite tolerado ({limite_dor_dia}) para o D+{dia}."
        elif febre or inchaco:
            motivo = f"Sintomas locais/sistêmicos identificados (Febre: {'Sim' if febre else 'Não'}, Edema: {'Sim' if inchaco else 'Não'}) no D+{dia}."
        else:
            motivo = "Evolução dentro do esperado para o protocolo."

        return EvaluationResult(
            alerta=alerta,
            status=status,
            motivo=motivo,
            score_sugerido=score,
        )