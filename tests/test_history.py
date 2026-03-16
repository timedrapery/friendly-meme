"""Tests for pali_translator.gui.history — HistoryStore bounded deque."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pali_translator.gui.history import HistoryStore


def _make_session(source: str = "dukkha") -> MagicMock:
    """Return a minimal fake TranslationSession mock."""
    s = MagicMock()
    s.source_text = source
    return s


class TestHistoryStoreInit(unittest.TestCase):
    def test_empty_at_start(self):
        store = HistoryStore()
        self.assertEqual(len(store), 0)

    def test_default_maxlen(self):
        store = HistoryStore()
        self.assertEqual(store.maxlen, 25)

    def test_custom_maxlen(self):
        store = HistoryStore(maxlen=5)
        self.assertEqual(store.maxlen, 5)

    def test_invalid_maxlen_raises(self):
        with self.assertRaises(ValueError):
            HistoryStore(maxlen=0)

    def test_bool_empty(self):
        self.assertFalse(HistoryStore())


class TestHistoryStoreAdd(unittest.TestCase):
    def test_add_single(self):
        store = HistoryStore()
        store.add(_make_session("a"))
        self.assertEqual(len(store), 1)

    def test_add_multiple(self):
        store = HistoryStore()
        for i in range(5):
            store.add(_make_session(str(i)))
        self.assertEqual(len(store), 5)

    def test_exceeds_capacity_drops_oldest(self):
        store = HistoryStore(maxlen=3)
        sessions = [_make_session(str(i)) for i in range(5)]
        for s in sessions:
            store.add(s)
        self.assertEqual(len(store), 3)
        # Most-recent-first: 4, 3, 2
        all_sessions = store.get_all()
        self.assertIs(all_sessions[0], sessions[4])
        self.assertIs(all_sessions[2], sessions[2])

    def test_bool_non_empty(self):
        store = HistoryStore()
        store.add(_make_session())
        self.assertTrue(store)


class TestHistoryStoreGetAll(unittest.TestCase):
    def test_most_recent_first(self):
        store = HistoryStore()
        s1 = _make_session("first")
        s2 = _make_session("second")
        store.add(s1)
        store.add(s2)
        result = store.get_all()
        self.assertIs(result[0], s2)
        self.assertIs(result[1], s1)

    def test_get_all_empty(self):
        store = HistoryStore()
        self.assertEqual(store.get_all(), [])

    def test_get_by_index(self):
        store = HistoryStore()
        s1 = _make_session("a")
        s2 = _make_session("b")
        store.add(s1)
        store.add(s2)
        self.assertIs(store.get(0), s2)  # most-recent
        self.assertIs(store.get(1), s1)

    def test_get_out_of_range_raises(self):
        store = HistoryStore()
        store.add(_make_session())
        with self.assertRaises(IndexError):
            store.get(5)


class TestHistoryStoreClear(unittest.TestCase):
    def test_clear(self):
        store = HistoryStore()
        store.add(_make_session())
        store.clear()
        self.assertEqual(len(store), 0)
        self.assertEqual(store.get_all(), [])


class TestHistoryStoreResize(unittest.TestCase):
    def test_grow_maxlen(self):
        store = HistoryStore(maxlen=3)
        for i in range(3):
            store.add(_make_session(str(i)))
        store.maxlen = 10
        self.assertEqual(store.maxlen, 10)
        self.assertEqual(len(store), 3)  # existing items preserved

    def test_shrink_drops_oldest(self):
        store = HistoryStore(maxlen=5)
        sessions = [_make_session(str(i)) for i in range(5)]
        for s in sessions:
            store.add(s)
        store.maxlen = 2
        self.assertEqual(len(store), 2)
        kept = store.get_all()
        # Most recent 2: sessions[4] and sessions[3]
        self.assertIn(sessions[4], kept)
        self.assertIn(sessions[3], kept)

    def test_invalid_maxlen_setter_raises(self):
        store = HistoryStore()
        with self.assertRaises(ValueError):
            store.maxlen = 0


if __name__ == "__main__":
    unittest.main()
