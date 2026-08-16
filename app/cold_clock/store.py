"""Persistence adapters for ColdClock cases."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol


class CaseStore(Protocol):
    def put(self, case: dict[str, Any]) -> None: ...

    def get(self, case_id: str) -> dict[str, Any] | None: ...

    def list_cases(self) -> list[dict[str, Any]]: ...

    def clear(self) -> None: ...


class MemoryCaseStore:
    def __init__(self) -> None:
        self._cases: dict[str, dict[str, Any]] = {}

    def put(self, case: dict[str, Any]) -> None:
        self._cases[case["case_id"]] = deepcopy(case)

    def get(self, case_id: str) -> dict[str, Any] | None:
        case = self._cases.get(case_id)
        return deepcopy(case) if case is not None else None

    def list_cases(self) -> list[dict[str, Any]]:
        return sorted((deepcopy(case) for case in self._cases.values()), key=lambda case: case["created_at"], reverse=True)

    def clear(self) -> None:
        self._cases.clear()


class FirestoreCaseStore:
    """Small Firestore adapter; local tests never require credentials."""

    def __init__(self, client: Any, collection: str = "cold_clock_cases") -> None:
        self._collection = client.collection(collection)

    def put(self, case: dict[str, Any]) -> None:
        self._collection.document(case["case_id"]).set(case)

    def get(self, case_id: str) -> dict[str, Any] | None:
        snapshot = self._collection.document(case_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list_cases(self) -> list[dict[str, Any]]:
        cases = [snapshot.to_dict() for snapshot in self._collection.stream()]
        return sorted(cases, key=lambda case: case["created_at"], reverse=True)

    def clear(self) -> None:
        for document in self._collection.stream():
            document.reference.delete()

