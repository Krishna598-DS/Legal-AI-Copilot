"""Abstract provider interface for professional discovery."""

from __future__ import annotations

from typing import Any, Protocol


class ProfessionalDirectoryProvider(Protocol):
    """
    Pluggable directory backend.

    The local provider reads/writes `LegalProfessional` rows.
    Future adapters (external APIs) can implement the same methods
    without changing route handlers.
    """

    name: str

    def list_professionals(
        self,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def search_by_specialization(
        self,
        specialization: str,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def search_by_city(
        self,
        city: str,
        *,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def get_professional(self, professional_id: str) -> dict[str, Any] | None: ...

    def create_professional(self, data: dict[str, Any]) -> dict[str, Any]: ...

    def update_professional(
        self, professional_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    def delete_professional(self, professional_id: str) -> bool: ...
