"""Entrypoint da API RESTful (FastAPI) do VitaVoz Clinical OS."""

import os
import sys
from pathlib import Path

# Injeção dinâmica da raiz do projeto no sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from src.config.settings import settings
from src.core.bootstrap import AppContainer
from src.database.seed.demo_seed import initialize_database

if not os.path.exists(settings.DB_NAME):
    initialize_database()

app = FastAPI(
    title="VitaVoz Clinical OS API",
    description="API RESTful para triagem preditiva pós-operatória e integração por IA.",
    version="1.0.0",
)


def get_services() -> dict:
    """Fábrica de injeção de dependências no FastAPI."""
    container = AppContainer()
    return container.resolve()


class WhatsAppPayload(BaseModel):
    phone: str
    message: str
    context_day: int = 3


@app.get("/api/v1/dashboard/summary", tags=["Analytics"])
def get_dashboard_summary(services: dict = Depends(get_services)):
    """Retorna os KPIs executivos da clínica."""
    try:
        patient_service = services["patient_service"]
        return patient_service.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/api/v1/patients/queue", tags=["Operação Clínica"])
def get_patient_queue(services: dict = Depends(get_services)):
    """Retorna a fila de pacientes ordenada por prioridade de risco."""
    try:
        patient_repo = services["patient_repo"]
        return patient_repo.get_fila_completa()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.post("/api/v1/webhooks/whatsapp", tags=["Integrações"])
def receive_whatsapp_message(
    payload: WhatsAppPayload, services: dict = Depends(get_services)
):
    """Webhook para ingestão e processamento de relatos do WhatsApp via IA."""
    try:
        handler = services["whatsapp_webhook_handler"]
        result = handler.process_incoming_payload(
            sender_phone=payload.phone,
            text_content=payload.message,
            dia_contexto=payload.context_day,
        )

        if result.get("status") == "patient_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Telefone não cadastrado na base de pacientes.",
            )

        return {
            "message": "Relato processado e risco atualizado com sucesso.",
            "status": "success",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/health", tags=["Infraestrutura"])
def health_check():
    """Endpoint de verificação de liveness."""
    return {"status": "healthy", "version": "1.0.0"}