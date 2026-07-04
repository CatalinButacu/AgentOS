from __future__ import annotations

import sqlite3


class KeyValueStore:
    def get(self, namespace: str, key: str) -> bytes | None:
        raise NotImplementedError

    def put(self, namespace: str, key: str, value: bytes) -> None:
        raise NotImplementedError

    def items(self, namespace: str) -> list[tuple[str, bytes]]:
        raise NotImplementedError


class InMemoryStore(KeyValueStore):
    def __init__(self) -> None:
        self._data: dict[str, dict[str, bytes]] = {}

    def get(self, namespace: str, key: str) -> bytes | None:
        return self._data.get(namespace, {}).get(key)

    def put(self, namespace: str, key: str, value: bytes) -> None:
        self._data.setdefault(namespace, {})[key] = value

    def items(self, namespace: str) -> list[tuple[str, bytes]]:
        return list(self._data.get(namespace, {}).items())


class SqliteStore(KeyValueStore):
    def __init__(self, path: str) -> None:
        self._connection = sqlite3.connect(path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS kv "
            "(namespace TEXT, key TEXT, value BLOB, PRIMARY KEY (namespace, key))")
        self._connection.commit()

    def get(self, namespace: str, key: str) -> bytes | None:
        row = self._connection.execute(
            "SELECT value FROM kv WHERE namespace = ? AND key = ?", (namespace, key)).fetchone()
        return bytes(row[0]) if row else None

    def put(self, namespace: str, key: str, value: bytes) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO kv (namespace, key, value) VALUES (?, ?, ?)",
            (namespace, key, sqlite3.Binary(value)))
        self._connection.commit()

    def items(self, namespace: str) -> list[tuple[str, bytes]]:
        rows = self._connection.execute(
            "SELECT key, value FROM kv WHERE namespace = ?", (namespace,)).fetchall()
        return [(key, bytes(value)) for key, value in rows]

    def close(self) -> None:
        self._connection.close()
