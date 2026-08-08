"""Fallback Provider."""
from src.ai.providers.base_provider import BaseAIProvider
class FallbackAIProvider(BaseAIProvider):
    def __init__(self, providers): self.providers = providers
    def process_patient_relato(self, a, r, c, f="audio.wav"):
        for p in self.providers:
            try: return p.process_patient_relato(a, r, c, f)
            except: continue
        raise Exception("Todos os provedores de IA falharam.")
    def transcribe_audio(self, a, f): pass
    def extract_clinical_data(self, t, c): pass
