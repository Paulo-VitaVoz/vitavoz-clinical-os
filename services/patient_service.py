"""Patient Service."""
from src.domain.dtos.clinic_summary_dto import ClinicSummaryDTO

class PatientService:
    def __init__(self, repo, proto_repo, dash_repo):
        self.repo = repo
        self.proto_repo = proto_repo
        self.dash_repo = dash_repo

    def get_patient_by_id(self, pid): return self.repo.get_patient_by_id(pid)
    def change_patient_protocol(self, pid, proto_id): return self.repo.update_patient_protocol(pid, proto_id)
    def get_dashboard_summary(self): return self.dash_repo.get_clinic_summary()
