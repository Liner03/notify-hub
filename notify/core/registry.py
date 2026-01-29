from typing import Dict, Type

from notify.channels.base import BaseNotifier


class NotifierRegistry:
    _registry: Dict[str, Type[BaseNotifier]] = {}

    @classmethod
    def register(cls, name: str, notifier_cls: Type[BaseNotifier]) -> None:
        cls._registry[name] = notifier_cls

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseNotifier:
        if name not in cls._registry:
            raise ValueError(f"unknown notifier type: {name}")
        return cls._registry[name](**kwargs)
