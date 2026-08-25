"""Persistence adapters for ColdClock cases."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol

DEFAULT_LIST_LIMIT = 60


class ConcurrentWriteError(RuntimeError):
    """Raised when a caller attempts to overwrite a newer persisted record."""

    def __init__(self, record_id: str, expected: int, actual: int) -> None:
        self.record_id = record_id
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Stale case {record_id}: expected version {expected}, current version is {actual}."
        )


def _recency(case: dict[str, Any]) -> str:
    return str(case.get("opened_at") or case.get("created_at") or "")


class CaseStore(Protocol):
    def put(self, case: dict[str, Any]) -> None: ...

    def get(self, case_id: str) -> dict[str, Any] | None: ...

    def list_cases(self, limit: int = DEFAULT_LIST_LIMIT) -> list[dict[str, Any]]: ...

    def list_cases_in_area(self, service_area: str) -> list[dict[str, Any]]: ...

    def clear(self) -> None: ...


class MemoryCaseStore:
    def __init__(self) -> None:
        self._cases: dict[str, dict[str, Any]] = {}

    def put(self, case: dict[str, Any]) -> None:
        case_id = case["case_id"]
        expected = int(case.get("record_version", 0))
        current = self._cases.get(case_id)
        actual = int(current.get("record_version", 0)) if current is not None else 0
        if (current is None and expected != 0) or (current is not None and expected != actual):
            raise ConcurrentWriteError(case_id, expected, actual)
        case["record_version"] = actual + 1
        self._cases[case_id] = deepcopy(case)

    def get(self, case_id: str) -> dict[str, Any] | None:
        case = self._cases.get(case_id)
        return deepcopy(case) if case is not None else None

    def list_cases(self, limit: int = DEFAULT_LIST_LIMIT) -> list[dict[str, Any]]:
        ordered = sorted((deepcopy(case) for case in self._cases.values()), key=_recency, reverse=True)
        return ordered[:limit] if limit else ordered

    def list_cases_in_area(self, service_area: str) -> list[dict[str, Any]]:
        return [deepcopy(case) for case in self._cases.values() if str(case.get("service_area") or "") == service_area]

    def clear(self) -> None:
        self._cases.clear()


class FirestoreCaseStore:
    """Small Firestore adapter; local tests never require credentials."""

    def __init__(self, client: Any, collection: str = "cold_clock_cases") -> None:
        self._client = client
        self._collection = client.collection(collection)

    def put(self, case: dict[str, Any]) -> None:
        from google.cloud import firestore

        case_id = case["case_id"]
        expected = int(case.get("record_version", 0))
        reference = self._collection.document(case_id)

        @firestore.transactional
        def commit(transaction: Any) -> int:
            snapshot = reference.get(transaction=transaction)
            current = snapshot.to_dict() if snapshot.exists else None
            actual = int(current.get("record_version", 0)) if current is not None else 0
            if (current is None and expected != 0) or (current is not None and expected != actual):
                raise ConcurrentWriteError(case_id, expected, actual)
            next_version = actual + 1
            payload = deepcopy(case)
            payload["record_version"] = next_version
            transaction.set(reference, payload)
            return next_version

        case["record_version"] = commit(self._client.transaction())

    def get(self, case_id: str) -> dict[str, Any] | None:
        snapshot = self._collection.document(case_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def list_cases(self, limit: int = DEFAULT_LIST_LIMIT) -> list[dict[str, Any]]:
        """Most recently opened cases first. Bounded so the queue stays fast as the public store grows."""
        from google.cloud import firestore

        query = self._collection.order_by("opened_at", direction=firestore.Query.DESCENDING)
        if limit:
            query = query.limit(limit)
        return [snapshot.to_dict() for snapshot in query.stream()]

    def list_cases_in_area(self, service_area: str) -> list[dict[str, Any]]:
        from google.cloud import firestore

        query = self._collection.where(filter=firestore.FieldFilter("service_area", "==", service_area))
        return [snapshot.to_dict() for snapshot in query.stream()]

    def clear(self) -> None:
        for document in self._collection.stream():
            document.reference.delete()
