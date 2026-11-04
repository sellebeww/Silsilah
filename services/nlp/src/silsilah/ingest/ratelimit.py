# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""Rate limit jendela tetap tanpa menyimpan IP atau ID mentah."""

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable


class RateLimiter:
    """Kunci (IP/ID) di-HMAC dengan garam acak; garam dan semua hitungan dibuang tiap jendela berakhir,
    jadi hash tidak bisa dibalik dan tidak bisa dikaitkan antar jendela."""

    def __init__(
        self, limit: int, window_s: float = 3600.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window_s = window_s
        self._clock = clock
        self._window_end = float("-inf")
        self._salt = b""
        # shortcut: hitungan di memori per proses; jalankan satu worker, atau pindah ke Redis bila diskalakan
        self._counts: dict[bytes, int] = {}

    def hit(self, key: str) -> float | None:
        """Catat satu permintaan; kembalikan detik sampai boleh mencoba lagi bila batas terlampaui."""
        now = self._clock()
        if now >= self._window_end:
            self._salt = secrets.token_bytes(32)
            self._counts.clear()
            self._window_end = now + self._window_s
        digest = hmac.new(self._salt, key.encode(), hashlib.sha256).digest()
        count = self._counts.get(digest, 0) + 1
        self._counts[digest] = count
        return None if count <= self._limit else self._window_end - now
