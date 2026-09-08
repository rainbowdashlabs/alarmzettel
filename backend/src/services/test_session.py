import unittest
from datetime import timedelta

from data.store import SessionStore
from entities.alarm import Alarm, Arbeitsmappe


class SessionStoreTest(unittest.TestCase):
    def test_created_session_is_retrievable(self):
        store = SessionStore(timedelta(minutes=30))
        session = store.create()
        self.assertIsNotNone(store.get(session.id))

    def test_unknown_session_is_none(self):
        self.assertIsNone(SessionStore(timedelta(minutes=30)).get("nope"))

    def test_expired_session_is_gone(self):
        store = SessionStore(timedelta(seconds=-1))
        session = store.create()
        self.assertIsNone(store.get(session.id))
        self.assertEqual(0, len(store))

    def test_access_pushes_expiry_back(self):
        store = SessionStore(timedelta(minutes=30))
        session = store.create()
        store.get(session.id)
        original = session.expires_at
        refreshed = store.get(session.id)
        self.assertGreaterEqual(refreshed.expires_at, original)

    def test_sweep_removes_only_expired(self):
        store = SessionStore(timedelta(minutes=30))
        alive = store.create()
        stale = store.create()
        stale.expires_at -= timedelta(hours=2)
        self.assertEqual(1, store.sweep())
        self.assertEqual(1, len(store))
        self.assertIsNotNone(store.get(alive.id))

    def test_dropping_a_session_reports_whether_it_existed(self):
        store = SessionStore(timedelta(minutes=30))
        session = store.create()
        self.assertTrue(store.drop(session.id))
        self.assertFalse(store.drop(session.id))

    def test_arbeitsmappe_round_trips(self):
        store = SessionStore(timedelta(minutes=30))
        session = store.create()
        session.arbeitsmappe = Arbeitsmappe(alarme=[Alarm(id="a", stichwort="BRAND K.")])
        self.assertEqual("BRAND K.", store.get(session.id).arbeitsmappe.alarme[0].stichwort)


if __name__ == "__main__":
    unittest.main()
