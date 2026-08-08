from abc import ABC, abstractmethod
from typing import Callable, Type

from src.domain.events import BaseEvent


class IEventDispatcher(ABC):
    """Contrato para qualquer dispatcher de eventos."""

    @abstractmethod
    def register_listener(
        self,
        event_type: Type[BaseEvent],
        listener: Callable[..., None],
        priority: int = 10,
    ) -> None:
        pass

    @abstractmethod
    def dispatch(self, event: BaseEvent) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass