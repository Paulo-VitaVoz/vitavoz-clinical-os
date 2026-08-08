"""Gemini Provider (Placeholder)."""
from src.ai.providers.base_provider import BaseAIProvider
class GeminiProvider(BaseAIProvider):
    def transcribe_audio(self, a, f): raise NotImplementedError()
    def extract_clinical_data(self, t, c): raise NotImplementedError()
    def process_patient_relato(self, a, r, c, f=""): raise NotImplementedError()
