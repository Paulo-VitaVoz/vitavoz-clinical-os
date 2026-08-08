"""Container de Injeção de Dependências (Composition Root) do VitaVoz Clinical OS."""

from typing import Any, Dict
import streamlit as st

from src.ai.providers.fallback_provider import FallbackAIProvider
from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.mock_provider import MockAIProvider
from src.ai.providers.openai_provider import OpenAIProvider
from src.config.settings import settings
from src.core.event_dispatcher import EventDispatcher
from src.core.event_serializer import EventSerializer
from src.core.failure_policy import DefaultFailurePolicy
from src.database.connection import get_connection
from src.domain.events import CriticalAlertGenerated
from src.integrations.whatsapp.mock_whatsapp_adapter import MockWhatsAppAdapter
from src.integrations.whatsapp.webhook_handler import WhatsAppWebhookHandler
from src.repositories.care_event_repository_impl import CareEventRepository
from src.repositories.clinic_dashboard_repository_impl import ClinicDashboardRepository
from src.repositories.evolution_repository import EvolutionRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.protocol_repository_impl import ProtocolRepositoryImpl
from src.services.clinical_service import ClinicalService
from src.services.evolution_service import EvolutionService
from src.services.patient_service import PatientService
from src.services.pdf_report_service import PDFReportService
from src.services.protocol_service import ProtocolService


def ui_notification_listener(event: CriticalAlertGenerated) -> None:
    """Ouvinte de eventos que enfileira alertas visuais no Streamlit."""
    try:
        if "pending_notifications" not in st.session_state:
            st.session_state["pending_notifications"] = []
        st.session_state["pending_notifications"].append(
            {
                "paciente_id": event.patient_id,
                "mensagem": f"Alerta Crítico: {event.patient_name} ({event.alert_status} - VitaScore™: {event.vitascore})",
            }
        )
    except Exception:
        # Quando executado via FastAPI ou fora da sessão Streamlit
        pass


class AppContainer:
    """Garante a instanciação unificada e controlada de todas as dependências."""

    def __init__(self) -> None:
        self.services: Dict[str, Any] = {}

    def resolve(self) -> Dict[str, Any]:
        """Resolve o grafo de dependências da aplicação."""
        if self.services:
            return self.services

        conn_factory = get_connection
        patient_repo = PatientRepository(conn_factory)
        evolution_repo = EvolutionRepository(conn_factory)
        protocol_repo = ProtocolRepositoryImpl(conn_factory)
        dashboard_repo = ClinicDashboardRepository(conn_factory)
        care_event_repo = CareEventRepository(conn_factory)

        whatsapp_adapter = MockWhatsAppAdapter()

        if settings.USE_MOCK_AI:
            ai_provider = MockAIProvider()
        else:
            ai_provider = FallbackAIProvider([
                OpenAIProvider(),
                GeminiProvider(),
                MockAIProvider()
            ])

        serializer = EventSerializer()
        failure_policy = DefaultFailurePolicy(serializer)
        event_dispatcher = EventDispatcher(failure_policy=failure_policy, max_workers=5)

        event_dispatcher.register_listener(
            CriticalAlertGenerated, ui_notification_listener, priority=0
        )

        protocol_service = ProtocolService(protocol_repo)
        evolution_service = EvolutionService(
            repo=evolution_repo,
            protocol_service=protocol_service,
            care_event_repo=care_event_repo,
            ai_provider=ai_provider,
            patient_repo=patient_repo,
            event_dispatcher=event_dispatcher,
        )

        patient_service = PatientService(patient_repo, protocol_repo, dashboard_repo)
        clinical_service = ClinicalService(evolution_repo, care_event_repo)
        pdf_report_service = PDFReportService()
        whatsapp_webhook_handler = WhatsAppWebhookHandler(
            patient_repo, evolution_service, whatsapp_adapter
        )

        self.services = {
            "patient_repo": patient_repo,
            "evolution_repo": evolution_repo,
            "protocol_repo": protocol_repo,
            "dashboard_repo": dashboard_repo,
            "care_event_repo": care_event_repo,
            "protocol_service": protocol_service,
            "evolution_service": evolution_service,
            "patient_service": patient_service,
            "clinical_service": clinical_service,
            "pdf_report_service": pdf_report_service,
            "whatsapp_webhook_handler": whatsapp_webhook_handler,
            "whatsapp_adapter": whatsapp_adapter,
            "event_dispatcher": event_dispatcher,
        }

        return self.services