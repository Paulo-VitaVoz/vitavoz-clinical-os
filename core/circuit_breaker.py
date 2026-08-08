"""Padrão Circuit Breaker para proteção contra falhas em cascata em APIs externas."""

import logging
import time
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Estados operacionais do disjuntor de proteção."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Garante o isolamento de serviços de terceiros quando ocorrem falhas recorrentes."""

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 30) -> None:
        self.name: str = name
        self.failure_threshold: int = failure_threshold
        self.recovery_timeout: int = recovery_timeout
        self.failures: int = 0
        self.state: CircuitState = CircuitState.CLOSED
        self.last_failure_time: float = 0.0

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executa a função monitorada aplicando as regras de transição de estado.

        Args:
            func: Função alvo a ser executada.
            *args: Argumentos posicionais.
            **kwargs: Argumentos nomeados.

        Returns:
            Any: Retorno da execução da função alvo.

        Raises:
            ConnectionError: Se o circuito estiver em estado OPEN.
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(f"[CircuitBreaker] {self.name} alterado para HALF_OPEN.")
                self.state = CircuitState.HALF_OPEN
            else:
                raise ConnectionError(f"Circuit Breaker '{self.name}' está OPEN. Requisição interrompida.")

        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def record_failure(self) -> None:
        """Registra a ocorrência de falha e avalia a abertura do circuito."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN) and self.failures >= self.failure_threshold:
            logger.warning(f"[CircuitBreaker] {self.name} atingiu {self.failures} falhas. Alterando para OPEN.")
            self.state = CircuitState.OPEN

    def reset(self) -> None:
        """Reseta o contador e retorna o circuito para o estado CLOSED."""
        self.failures = 0
        self.state = CircuitState.CLOSED