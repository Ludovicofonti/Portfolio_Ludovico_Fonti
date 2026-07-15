"""Contratto comune per provider on-chain futuri."""

from abc import ABC, abstractmethod
from datetime import datetime


class OnChainSource(ABC):
    @abstractmethod
    def fetch(self, network: str, metric: str, start_time: datetime,
              end_time: datetime, frequency: str):
        """Restituisce record con observation_time e available_time distinti."""
        raise NotImplementedError
