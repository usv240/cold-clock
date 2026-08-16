"""Construct the same wake runtime for local tests and Cloud Run."""

from __future__ import annotations

import os

from spine.clock import MemoryClockStateStore, SimulatedClock
from spine.firestore_wakes import FirestoreClockStateStore, FirestoreWakeStore
from spine.wake import MemoryWakeStore, WakeScheduler


def build_runtime(project: str, use_firestore: bool):
    if use_firestore:
        from google.cloud import firestore

        client = firestore.Client(project=project)
        clock = SimulatedClock(FirestoreClockStateStore(client, "cold-clock"))
        wake_store = FirestoreWakeStore(client, "cold_clock_wakes")
    else:
        clock = SimulatedClock(MemoryClockStateStore())
        wake_store = MemoryWakeStore()
    scheduler = WakeScheduler(
        wake_store,
        clock,
        lease_seconds=int(os.environ.get("WAKE_LEASE_SECONDS", "90")),
        max_attempts=int(os.environ.get("WAKE_MAX_ATTEMPTS", "5")),
    )
    return clock, scheduler
