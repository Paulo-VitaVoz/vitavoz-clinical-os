"""Módulo de configurações globais e variáveis de ambiente do VitaVoz."""

import os
from datetime import datetime


class Settings:
    """Carrega e centraliza as configurações da aplicação."""

    def __init__(self) -> None:
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL", "sqlite:///vitavoz_production.db"
        )
        self.DB_NAME: str = os.getenv("DB_NAME", "vitavoz_production.db")
        self.HOJE: datetime = datetime(2026, 7, 28)

        self.UPLOADS_DIR: str = "uploads"
        os.makedirs(self.UPLOADS_DIR, exist_ok=True)

        self.USE_MOCK_AI: bool = (
            os.getenv("USE_MOCK_AI", "true").lower() in ("true", "1", "yes")
        )
        self.AI_TIMEOUT_SECONDS: float = float(
            os.getenv("AI_TIMEOUT_SECONDS", "8.0")
        )

        # Chaves de APIs de IA
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

        # Autenticação JWT
        self.JWT_SECRET_KEY: str = os.getenv(
            "JWT_SECRET_KEY", "vitavoz_clinical_os_production_secret_key_2026"
        )
        self.JWT_ALGORITHM: str = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

        # Parametrização B2B de ROI Executivo
        self.ROI_COST_PER_READMISSION_BRL: float = float(
            os.getenv("ROI_COST_PER_READMISSION_BRL", "3500.0")
        )
        self.ROI_HOURLY_STAFF_COST_BRL: float = float(
            os.getenv("ROI_HOURLY_STAFF_COST_BRL", "120.0")
        )
        self.ROI_MINUTES_SAVED_PER_REPORT: float = float(
            os.getenv("ROI_MINUTES_SAVED_PER_REPORT", "8.0")
        )


# Instância Singleton oficial da aplicação
settings = Settings()

# Aliases de nível de módulo para compatibilidade de importação direta
DATABASE_URL: str = settings.DATABASE_URL
DB_NAME: str = settings.DB_NAME
HOJE: datetime = settings.HOJE
USE_MOCK_AI: bool = settings.USE_MOCK_AI
ROI_COST_PER_READMISSION_BRL: float = settings.ROI_COST_PER_READMISSION_BRL
ROI_HOURLY_STAFF_COST_BRL: float = settings.ROI_HOURLY_STAFF_COST_BRL
ROI_MINUTES_SAVED_PER_REPORT: float = settings.ROI_MINUTES_SAVED_PER_REPORT