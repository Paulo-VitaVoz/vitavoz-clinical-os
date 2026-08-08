"""Dispatcher de eventos assíncrono e não-bloqueante para o VitaVoz."""

import logging
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Tuple, Type, Protocol
from src.domain.events import BaseEvent
from src.core.event_serializer import EventSerializer
from src.core.failure_policy import DefaultFailurePolicy, IFailurePolicy

logger = logging.getLogger(__name__)


class IEventDispatcher(Protocol):
    """Contrato base para o Event Dispatcher."""
    def register_listener(
        self, event_type: Type[BaseEvent], listener: Callable[..., None], priority: int = 10
    ) -> None:
        ...

    def dispatch(self, event: BaseEvent) -> None:
        ...

    def shutdown(self) -> None:
        ...


class EventDispatcher(IEventDispatcher):
    def __init__(
        self,
        failure_policy: IFailurePolicy | None = None,
        max_workers: int = 5,
    ) -> None:
        self._listeners: Dict[Type[BaseEvent], List[Tuple[int, Callable[..., None]]]] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="event_worker")
        self._serializer = EventSerializer()
        self._failure_policy = failure_policy or DefaultFailurePolicy(self._serializer)

    def register_listener(
        self, event_type: Type[BaseEvent], listener: Callable[..., None], priority: int = 10
    ) -> None:
        """Inscreve uma função ouvinte ordenando por prioridade."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append((priority, listener))
        self._listeners[event_type].sort(key=lambda item: item[0])

    def dispatch(self, event: BaseEvent) -> None:
        """Publica o evento para todos os ouvintes registrados."""
        event_type = type(event)

        if event_type in self._listeners:
            for _, listener in self._listeners[event_type]:
                self._executor.submit(self._safe_execute_with_retry, listener, event)

        if BaseEvent in self._listeners and event_type != BaseEvent:
            for _, listener in self._listeners[BaseEvent]:
                self._executor.submit(self._safe_execute_with_retry, listener, event)

    def _safe_execute_with_retry(
        self, listener: Callable[..., None], event: BaseEvent, max_retries: int = 3
    ) -> None:
        """Executa a função ouvinte com retries em caso de falha transitória."""
        last_exception = Exception("Unknown Error")
        last_stacktrace = ""

        for attempt in range(1, max_retries + 1):
            try:
                listener(event)
                return
            except Exception as e:
                last_exception = e
                last_stacktrace = traceback.format_exc()
                logger.warning(
                    f"Tentativa {attempt}/{max_retries} falhou no listener {listener.__name__}: {e}"
                )
                time.sleep(0.02 * attempt)

        self._failure_policy.handle_exhausted_retries(
            listener.__name__, event, last_exception, last_stacktrace
        )

    def shutdown(self) -> None:
        """Encerra graciosamente as worker threads em execução."""
        self._executor.shutdown(wait=False)