"""in-memory trie helpers for deterministic keyword searches over SDE names"""

from __future__ import annotations

from heapq import nsmallest
from threading import RLock
from typing import Callable, Iterable

from etu.sde.database import DB_PATH


class _TrieNode:
    """Compact node used by :class:`KeywordTrieIndex`."""

    __slots__ = ("children", "row_indexes")

    def __init__(self):
        self.children: dict[str, _TrieNode] = {}
        self.row_indexes: list[int] | None = None


class KeywordTrieIndex:
    """
    Search immutable SDE rows with a suffix trie over whitespace-delimited words.

    Each word contributes all of its suffixes to the trie.  Looking up a query
    keyword therefore preserves the application's existing ``contains``
    semantics while avoiding a full SQL/name scan on every keystroke.  Multiple
    query keywords are intersected, so every keyword must still be present.
    """

    def __init__(
        self,
        rows: Iterable,
        *,
        name_key: str = "name",
        facet_keys: Iterable[str] = (),
    ):
        self._rows = tuple(
            dict(row)
            for row in rows
        )
        self._names = tuple(
            str(row[name_key])
            for row in self._rows
        )
        self._normalized_names = tuple(
            name.lower()
            for name in self._names
        )
        self._root = _TrieNode()
        self._facets = {
            key: {}
            for key in facet_keys
        }

        for row_index, normalized_name in enumerate(
            self._normalized_names
        ):
            # Repeated words in one name should not duplicate terminal indexes.
            words = dict.fromkeys(
                normalized_name.split()
            )

            for word in words:
                self._index_word(
                    word,
                    row_index,
                )

            row = self._rows[row_index]

            for key, values in self._facets.items():
                value = row.get(key)
                values.setdefault(value, set()).add(
                    row_index
                )

    def _index_word(
        self,
        word: str,
        row_index: int,
    ):
        for start in range(len(word)):
            node = self._root

            for character in word[start:]:
                child = node.children.get(
                    character
                )

                if child is None:
                    child = _TrieNode()
                    node.children[character] = child

                node = child

            if node.row_indexes is None:
                node.row_indexes = [row_index]

            elif node.row_indexes[-1] != row_index:
                node.row_indexes.append(
                    row_index
                )

    def _keyword_matches(
        self,
        keyword: str,
    ) -> set[int]:
        node = self._root

        for character in keyword:
            node = node.children.get(
                character
            )

            if node is None:
                return set()

        matches: set[int] = set()
        pending = [node]

        while pending:
            current = pending.pop()

            if current.row_indexes:
                matches.update(
                    current.row_indexes
                )

            pending.extend(
                current.children.values()
            )

        return matches

    def search(
        self,
        query: str,
        limit: int | None = 25,
        *,
        filters: dict[str, object] | None = None,
    ) -> list[dict]:
        keywords = [
            keyword.lower()
            for keyword in query.split()
            if keyword
        ]

        if not keywords:
            return []

        candidate_sets = [
            self._keyword_matches(keyword)
            for keyword in dict.fromkeys(keywords)
        ]

        if any(
            not candidates
            for candidates in candidate_sets
        ):
            return []

        candidate_sets.sort(key=len)
        candidates = candidate_sets[0]

        for other in candidate_sets[1:]:
            candidates.intersection_update(other)

            if not candidates:
                return []

        for key, value in (filters or {}).items():
            values = self._facets.get(key)

            if values is None:
                raise KeyError(
                    f"Unknown search facet: {key}"
                )

            candidates.intersection_update(
                values.get(value, ())
            )

            if not candidates:
                return []

        match_count = len(candidates)
        normalized_query = " ".join(keywords)

        def ranking(row_index: int):
            name = self._names[row_index]
            normalized_name = self._normalized_names[
                row_index
            ]

            if normalized_name == normalized_query:
                rank = 0

            elif normalized_name.startswith(
                normalized_query
            ):
                rank = 1

            else:
                rank = 2

            return (
                rank,
                len(name),
                normalized_name,
                name,
            )

        if limit is None:
            selected = sorted(
                candidates,
                key=ranking,
            )

        else:
            limit = max(1, int(limit))

            if match_count <= limit:
                selected = sorted(
                    candidates,
                    key=ranking,
                )
            else:
                selected = nsmallest(
                    limit,
                    candidates,
                    key=ranking,
                )

        output = []

        for row_index in selected:
            row = dict(
                self._rows[row_index]
            )
            row["match_count"] = match_count
            output.append(row)

        return output


class TrieIndexCache:
    """Thread-safe lazy cache that rebuilds indexes when the local DB changes."""

    def __init__(
        self,
        builder: Callable[..., KeywordTrieIndex],
    ):
        self._builder = builder
        self._lock = RLock()
        self._database_signature = None
        self._indexes: dict[tuple, KeywordTrieIndex] = {}

    @staticmethod
    def _signature():
        try:
            stat = DB_PATH.stat()
        except OSError:
            return None

        return (
            stat.st_mtime_ns,
            stat.st_size,
        )

    def get(self, *variant) -> KeywordTrieIndex:
        signature = self._signature()
        key = tuple(variant)

        with self._lock:
            if signature != self._database_signature:
                self._indexes.clear()
                self._database_signature = signature

            index = self._indexes.get(key)

            if index is None:
                index = self._builder(*variant)
                self._indexes[key] = index

            return index

    def clear(self):
        with self._lock:
            self._indexes.clear()
            self._database_signature = self._signature()
