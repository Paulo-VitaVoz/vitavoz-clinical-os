"""Entidade de Domínio representando um Protocolo Clínico."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Protocol:
    """Regras e parâmetros de acompanhamento pós-operatório."""

    nome_procedimento: str
    dias_acompanhamento_padrao: int
    alert_rules: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None

    def get_pain_threshold(self, dia: int, default_threshold: int = 3) -> int:
        """Retorna o limiar máximo de dor tolerado para um determinado dia pós-operatório."""
        limiares = self.alert_rules.get("limiares_dor", {})
        return limiares.get(str(dia), default_threshold)
