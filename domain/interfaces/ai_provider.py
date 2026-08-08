"""Port de Domínio para Provedores de Inteligência Artificial (Clean Architecture DIP)."""

from typing import Optional, Protocol
from src.domain.dtos.ai_analysis_result_dto import AIAnalysisResultDTO


class IAIProvider(Protocol):
    """Contrato abstrato de serviços de Inteligência Artificial e Transcrição."""

    def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        ...

    def extract_clinical_data(
        self, transcricao: str, contexto_dia: int
    ) -> AIAnalysisResultDTO:
        ...

    def process_patient_relato(
        self,
        audio_bytes: Optional[bytes],
        relato_texto: Optional[str],
        contexto_dia: int,
        filename: str = "audio.wav",
    ) -> AIAnalysisResultDTO:
        ...
