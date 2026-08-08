"""Mock AI Provider."""
import time
from src.ai.providers.base_provider import BaseAIProvider
from src.domain.dtos.ai_analysis_result_dto import AIAnalysisResultDTO

class MockAIProvider(BaseAIProvider):
    def transcribe_audio(self, audio_bytes, filename): return "Transcrição simulada."
    def extract_clinical_data(self, transcricao, contexto_dia):
        return AIAnalysisResultDTO(transcricao, 4, True, False, "Piorando", "Resumo", 95.0, "Mock")
    def process_patient_relato(self, audio_bytes, relato_texto, contexto_dia, filename="audio.wav"):
        time.sleep(1)
        texto = relato_texto or "Doutor, minha dor aumentou para 4 e estou com inchaço hoje."
        return AIAnalysisResultDTO(texto, 4, True, False, "Piorando", "Paciente relata dor moderada e inchaço no D+3.", 95.0, "Mock")
