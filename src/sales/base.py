from __future__ import annotations

from abc import ABC, abstractmethod


class SalesService(ABC):
    @abstractmethod
    def answer(self, question: str) -> str:
        """Answer a supported analytical question."""
