"""Idempotency guard: exactly one voice note per (target, response text)."""

from __future__ import annotations

import hashlib
import threading
from collections import OrderedDict


class DedupGuard:
    def __init__(self, capacity: int = 64) -> None:
        self._capacity = capacity
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def fingerprint(target: str, text: str) -> str:
        return hashlib.sha256(f"{target}\0{text.strip()}".encode()).hexdigest()

    def claim(self, target: str, text: str) -> bool:
        """Return True the first time a (target, text) pair is seen."""
        key = self.fingerprint(target, text)
        with self._lock:
            if key in self._seen:
                return False
            self._seen[key] = None
            while len(self._seen) > self._capacity:
                self._seen.popitem(last=False)
            return True
