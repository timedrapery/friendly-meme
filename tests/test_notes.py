"""Tests for pali_translator.gui.notes — NotesStore."""

from __future__ import annotations

import unittest

from pali_translator.gui.notes import NotesStore


class TestNotesStoreDefaults(unittest.TestCase):
    def test_session_note_empty(self):
        store = NotesStore()
        self.assertEqual(store.session_note, "")

    def test_token_notes_empty(self):
        store = NotesStore()
        self.assertEqual(store.token_notes, {})

    def test_phrase_notes_empty(self):
        store = NotesStore()
        self.assertEqual(store.phrase_notes, {})

    def test_is_empty_on_new_store(self):
        self.assertTrue(NotesStore().is_empty())


class TestSessionNote(unittest.TestCase):
    def test_set_and_get(self):
        store = NotesStore()
        store.set_session_note("My note about the passage.")
        self.assertEqual(store.session_note, "My note about the passage.")

    def test_clear_session_note(self):
        store = NotesStore()
        store.set_session_note("some note")
        store.clear_session_note()
        self.assertEqual(store.session_note, "")

    def test_not_empty_after_set(self):
        store = NotesStore()
        store.set_session_note("x")
        self.assertFalse(store.is_empty())


class TestTokenNotes(unittest.TestCase):
    def test_set_and_get(self):
        store = NotesStore()
        store.set_token_note("dukkha", "suffering or unsatisfactoriness")
        self.assertEqual(store.get_token_note("dukkha"), "suffering or unsatisfactoriness")

    def test_empty_string_removes_entry(self):
        store = NotesStore()
        store.set_token_note("dukkha", "note")
        store.set_token_note("dukkha", "")
        self.assertNotIn("dukkha", store.token_notes)

    def test_get_missing_key_returns_empty(self):
        store = NotesStore()
        self.assertEqual(store.get_token_note("missing"), "")

    def test_clear_token_note(self):
        store = NotesStore()
        store.set_token_note("nibbana", "cessation")
        store.clear_token_note("nibbana")
        self.assertEqual(store.get_token_note("nibbana"), "")

    def test_clear_missing_key_no_error(self):
        store = NotesStore()
        store.clear_token_note("ghost")

    def test_multiple_tokens(self):
        store = NotesStore()
        store.set_token_note("a", "note_a")
        store.set_token_note("b", "note_b")
        self.assertEqual(len(store.token_notes), 2)


class TestPhraseNotes(unittest.TestCase):
    def _key(self, *tokens):
        return NotesStore.span_key(tokens)

    def test_span_key_joins_with_underscore(self):
        key = NotesStore.span_key(("samma", "sankappa"))
        self.assertEqual(key, "samma_sankappa")

    def test_span_key_single_token(self):
        self.assertEqual(NotesStore.span_key(("dukkha",)), "dukkha")

    def test_set_and_get_phrase_note(self):
        store = NotesStore()
        key = self._key("bodhi", "citta")
        store.set_phrase_note(key, "mind of awakening")
        self.assertEqual(store.get_phrase_note(key), "mind of awakening")

    def test_get_missing_phrase_returns_empty(self):
        store = NotesStore()
        self.assertEqual(store.get_phrase_note("bodhi_citta"), "")

    def test_clear_phrase_note(self):
        store = NotesStore()
        key = self._key("samma", "sankappa")
        store.set_phrase_note(key, "right intention")
        store.clear_phrase_note(key)
        self.assertEqual(store.get_phrase_note(key), "")


class TestClearAll(unittest.TestCase):
    def test_clear_all_resets_everything(self):
        store = NotesStore()
        store.set_session_note("s")
        store.set_token_note("t", "note")
        store.set_phrase_note("p_q", "pq note")
        store.clear_all()
        self.assertTrue(store.is_empty())

    def test_is_empty_after_clear_all(self):
        store = NotesStore()
        store.set_session_note("s")
        store.clear_all()
        self.assertTrue(store.is_empty())


class TestToDict(unittest.TestCase):
    def test_empty_store_dict(self):
        d = NotesStore().to_dict()
        self.assertEqual(d, {"session_note": "", "token_notes": {}, "phrase_notes": {}})

    def test_round_trip(self):
        store = NotesStore()
        store.set_session_note("overview note")
        store.set_token_note("dukkha", "suffering")
        store.set_phrase_note("bodhi_citta", "mind of awakening")
        d = store.to_dict()
        self.assertEqual(d["session_note"], "overview note")
        self.assertEqual(d["token_notes"]["dukkha"], "suffering")
        self.assertEqual(d["phrase_notes"]["bodhi_citta"], "mind of awakening")

    def test_dict_is_json_serializable(self):
        import json
        store = NotesStore()
        store.set_session_note("note")
        result = json.dumps(store.to_dict())
        self.assertIn("note", result)


if __name__ == "__main__":
    unittest.main()
