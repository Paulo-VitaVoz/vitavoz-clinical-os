"""Enumeração dos tipos de eventos do ciclo do cuidado (Care Timeline)."""

from enum import Enum


class EventType(str, Enum):
    """Tipos de fatos clínicos imutáveis do ciclo do cuidado."""

    SURGERY_COMPLETED = "SURGERY_COMPLETED"
    PATIENT_RELATO = "PATIENT_RELATO"
    AI_ANALYSIS = "AI_ANALYSIS"
    DOCTOR_CONDUCT = "DOCTOR_CONDUCT"
    PATIENT_CONFIRM = "PATIENT_CONFIRM"
