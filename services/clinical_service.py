"""Clinical Service."""
from datetime import datetime
from src.domain.entities.evolution import Evolution
from src.domain.entities.care_event import CareEvent
from src.domain.enums.event_type import EventType

class ClinicalService:
    def __init__(self, evo_repo, care_repo):
        self.evo_repo = evo_repo
        self.care_repo = care_repo

    def resolve_evolution_alert(self, patient_id: int, evolution_id: int, conduct_text: str):
        hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.evo_repo.save_doctor_conduct(evolution_id, conduct_text, hoje)

        event = CareEvent(
            patient_id=patient_id, event_type=EventType.DOCTOR_CONDUCT, timestamp=hoje,
            title="Conduta Médica Registrada", description=conduct_text, author="Dr. Davi", badge_color="#3B82F6"
        )
        self.care_repo.add_event(event)
