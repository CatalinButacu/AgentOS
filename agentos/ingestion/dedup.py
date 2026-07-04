from __future__ import annotations

import hashlib
import math


class BloomFilter:
    def __init__(self, expected_items: int, false_positive_rate: float = 0.01) -> None:
        self.expected_items = max(1, expected_items)
        self.false_positive_rate = false_positive_rate
        self.size = self._optimal_size(self.expected_items, false_positive_rate)
        self.hash_count = self._optimal_hash_count(self.size, self.expected_items)
        self.bits = bytearray((self.size + 7) // 8)

    @staticmethod
    def _optimal_size(item_count: int, false_positive_rate: float) -> int:
        return max(1, math.ceil(-(item_count * math.log(false_positive_rate)) / (math.log(2) ** 2)))

    @staticmethod
    def _optimal_hash_count(size: int, item_count: int) -> int:
        return max(1, round((size / item_count) * math.log(2)))

    def _indices(self, item: str):
        digest = hashlib.blake2b(item.encode("utf-8"), digest_size=16).digest()
        step_a = int.from_bytes(digest[:8], "big")
        step_b = int.from_bytes(digest[8:], "big") | 1
        for probe in range(self.hash_count):
            yield (step_a + probe * step_b) % self.size

    def add(self, item: str) -> None:
        for index in self._indices(item):
            self.bits[index >> 3] |= 1 << (index & 7)

    def __contains__(self, item: str) -> bool:
        return all((self.bits[index >> 3] >> (index & 7)) & 1 for index in self._indices(item))


class ContentDeduper:
    def __init__(self, bloom: BloomFilter | None = None) -> None:
        self.bloom = bloom or BloomFilter(expected_items=100_000)
        self.confirmed: set[str] = set()

    def is_new(self, key: str) -> bool:
        if key not in self.bloom:
            self._register(key)
            return True
        if key in self.confirmed:
            return False
        self._register(key)
        return True

    def _register(self, key: str) -> None:
        self.bloom.add(key)
        self.confirmed.add(key)

    def __len__(self) -> int:
        return len(self.confirmed)


if __name__ == "__main__":
    deduper = ContentDeduper(BloomFilter(expected_items=1000))
    for content_hash in ["aaa", "bbb", "aaa", "ccc", "bbb"]:
        verdict = "new" if deduper.is_new(content_hash) else "duplicate"
        print(f"{content_hash}: {verdict}")
    print(f"unique={len(deduper)} bloom_bits={deduper.bloom.size} probes={deduper.bloom.hash_count}")
