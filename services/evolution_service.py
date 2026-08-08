"""Caso de Uso para Orquestração do Relato do Paciente."""

import uuid
from datetime import datetime
from typing import Optional
from src.config.settings import settings
from src.domain.entities.care_event import CareEvent
from src.domain.entities.evolution import Evolution
from src.domain.enums.event_type import EventType
from src.domain.events import CriticalAlertGenerated, EvolutionRegistered
from src.domain.interfaces.ai_provider import IAIProvider
from src.domain.interfaces.care_event_repository import ICareEventRepository
from src.domain.interfaces.event_dispatcher_interface import IEventDispatcher
from src.domain.interfaces.evolution_repository_interface import IEvolutionRepository
from src.domain.interfaces.patient_repository_interface import IPatientRepository
from src.services.protocol_service import ProtocolService


class EvolutionService:
    """Orquestra o processamento do relato por IA, atualização de score e emissão de eventos."""

    def __init__(
        self,
        repo: IEvolutionRepository,
        protocol_service: ProtocolService,
        care_event_repo: ICareEventRepository,
        ai_provider: IAIProvider,
        patient_repo: IPatientRepository,
        event_dispatcher: IEventDispatcher,
    ) -> None:
        self._repo = repo
        self._protocol_service = protocol_service
        self._care_event_repo = care_event_repo
        self._ai_provider = ai_provider
        self._patient_repo = patient_repo
        self._event_dispatcher = event_dispatcher

    def process_voice_report(
        self,
        patient_id: int,
        protocol_id: int,
        dia: int,
        nivel_dor: int,
        relato_texto: str,
        audio_bytes: Optional[bytes] = None,
    ) -> None:
        """Processa o relato, salva os dados no repositório e despacha os eventos no barramento."""
        if self._repo.has_evolution_for_day(patient_id, dia):
            return

        ai_result = self._ai_provider.process_patient_relato(
            audio_bytes=audio_bytes,
            relato_texto=relato_texto,
            contexto_dia=dia,
        )

        dor_efetiva = ai_result.dor_nivel if ai_result.dor_nivel is not None else nivel_dor
        texto_efetivo = ai_result.transcricao_texto if ai_result.transcricao_texto else relato_texto

        evaluation = self._protocol_service.evaluate_symptoms_against_protocol(
            protocol_id=protocol_id,
            dor=dor_efetiva,
            dia=dia,
            inchaco=ai_result.inchaco_detectado,
            febre=ai_result.febre_detectada,
            tendencia=ai_result.tendencia_identificada,
            sintomas_secundarios=ai_result.sintomas_secundarios,
            confianca_score=ai_result.confianca_score,
        )

        inchaco_str = "Sim" if ai_result.inchaco_detectado else "Não"
        febre_str = "Sim" if ai_result.febre_detectada else "Não"
        data_registro = settings.HOJE.strftime("%d/%m/%Y")

        nova_evolucao = Evolution(
            paciente_id=patient_id,
            dia=dia,
            dor=dor_efetiva,
            inchaco=inchaco_str,
            febre=febre_str,
            tendencia=ai_result.tendencia_identificada,
            relato=texto_efetivo,
            score=evaluation.score_sugerido,
            status_alerta=evaluation.status,
            data_registro=data_registro,
            motivo=evaluation.motivo,
        )

        self._repo.save_evolution(nova_evolucao)

        timestamp_atual = f"{data_registro} {datetime.now().strftime('%H:%M')}"

        self._care_event_repo.add_event(
            CareEvent(
                patient_id=patient_id,
                event_type=EventType.PATIENT_RELATO,
                timestamp=timestamp_atual,
                title=f"Relato Enviado (D+{dia})",
                description=f'"{texto_efetivo}" (Dor {dor_efetiva}/10)',
                author="Paciente",
                badge_color="#3B82F6",
            )
        )

        self._care_event_repo.add_event(
            CareEvent(
                patient_id=patient_id,
                event_type=EventType.AI_ANALYSIS,
                timestamp=timestamp_atual,
                title=f"Análise VitaVoz AI: {evaluation.status}",
                description=f"VitaScore™: {evaluation.score_sugerido}/100 | {ai_result.resumo_clinico}",
                author="VitaVoz AI",
                badge_color="#EF4444" if "🟡" in evaluation.status or "🔴" in evaluation.status else "#10B981",
            )
        )

        # Emissão de Eventos com Correlation ID
        correlation_id = str(uuid.uuid4())
        self._event_dispatcher.dispatch(
            EvolutionRegistered(
                correlation_id=correlation_id,
                patient_id=patient_id,
                dia=dia,
                vitascore=evaluation.score_sugerido,
                status_alerta=evaluation.status,
            )
        )

        if evaluation.status != "🟢 Normal":
            patient = self._patient_repo.get_patient_by_id(patient_id)
            patient_name = patient.nome if patient else f"ID {patient_id}"

            self._event_dispatcher.dispatch(
                CriticalAlertGenerated(
                    correlation_id=correlation_id,
                    patient_id=patient_id,
                    patient_name=patient_name,
                    vitascore=evaluation.score_sugerido,
                    alert_status=evaluation.status,
                    alert_reason=evaluation.motivo,
                )
            )