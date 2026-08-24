from copy import deepcopy

import pytest

from cold_clock.store import ConcurrentWriteError, MemoryCaseStore


def test_case_store_rejects_a_stale_whole_record_write():
    store = MemoryCaseStore()
    original = {"case_id": "cc-race", "created_at": "2026-08-24T00:00:00Z"}
    store.put(original)
    first_reader = store.get("cc-race")
    stale_reader = deepcopy(first_reader)

    first_reader["status"] = "reviewed"
    store.put(first_reader)

    stale_reader["status"] = "dispatched"
    with pytest.raises(ConcurrentWriteError) as error:
        store.put(stale_reader)

    assert error.value.expected == 1
    assert error.value.actual == 2
    assert store.get("cc-race")["status"] == "reviewed"


def test_case_store_versions_every_successful_write():
    store = MemoryCaseStore()
    case = {"case_id": "cc-version", "created_at": "2026-08-24T00:00:00Z"}
    store.put(case)
    assert case["record_version"] == 1
    store.put(case)
    assert case["record_version"] == 2
