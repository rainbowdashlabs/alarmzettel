import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data.dokument import TRENNER
from data.freigabe import FreigabeFehler, Freigaben

MAPPE = {"version": 1, "alarme": [{"id": "a1", "stichwort": "BRAND K."}]}


def pfad(*teile: str) -> str:
    return TRENNER.join(teile)


class FreigabenTest(unittest.TestCase):
    def setUp(self):
        self.verzeichnis = tempfile.TemporaryDirectory()
        self.freigaben = Freigaben(Path(self.verzeichnis.name), tage=30)

    def tearDown(self):
        self.verzeichnis.cleanup()

    def zurueckdatieren(self, token: str, tage: int):
        alt = (datetime.now(timezone.utc) - timedelta(days=tage)).isoformat()
        with self.freigaben._verbindung() as db:
            db.execute("UPDATE freigaben SET zuletzt = ? WHERE token = ?", (alt, token))

    def test_a_share_reads_back_what_was_stored(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        inhalt, _ = self.freigaben.lesen(token)
        self.assertEqual("BRAND K.", inhalt["alarme"][0]["stichwort"])

    def test_the_token_is_long_enough_not_to_be_guessed(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.assertGreaterEqual(len(token), 40)

    def test_two_shares_get_different_tokens(self):
        erst, _ = self.freigaben.anlegen(MAPPE)
        zweit, _ = self.freigaben.anlegen(MAPPE)
        self.assertNotEqual(erst, zweit)

    def test_an_unknown_token_is_refused(self):
        with self.assertRaises(FreigabeFehler):
            self.freigaben.lesen("gibtesnicht")

    def test_reading_pushes_the_expiry_out(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.zurueckdatieren(token, 20)
        _, laeuft_ab = self.freigaben.lesen(token)
        self.assertGreater(laeuft_ab, datetime.now(timezone.utc) + timedelta(days=29))

    def test_a_share_read_recently_survives_the_reaper(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.zurueckdatieren(token, 29)
        self.assertEqual(0, self.freigaben.aufraeumen())
        self.assertIsNotNone(self.freigaben.lesen(token))

    def test_a_share_unread_for_the_retention_is_reaped(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.zurueckdatieren(token, 31)
        self.assertEqual(1, self.freigaben.aufraeumen())
        with self.assertRaises(FreigabeFehler):
            self.freigaben.lesen(token)

    def test_the_reaper_removes_the_file_as_well_as_the_row(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.zurueckdatieren(token, 31)
        self.freigaben.aufraeumen()
        self.assertEqual([], list(Path(self.verzeichnis.name).glob("*.json")))

    def test_reading_keeps_a_share_alive_indefinitely(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        for _ in range(3):
            self.zurueckdatieren(token, 29)
            self.freigaben.lesen(token)
            self.assertEqual(0, self.freigaben.aufraeumen())

    def test_a_file_without_a_row_is_cleared_away(self):
        """A crash between writing the file and inserting the row leaves something unreachable."""
        verwaist = Path(self.verzeichnis.name) / "verwaist.json"
        verwaist.write_text("{}", encoding="utf-8")
        self.assertEqual(1, self.freigaben.aufraeumen())
        self.assertFalse(verwaist.exists())

    def test_a_row_without_a_file_reports_the_share_as_gone(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        (Path(self.verzeichnis.name) / f"{token}.json").unlink()
        with self.assertRaises(FreigabeFehler):
            self.freigaben.lesen(token)

    def test_deleting_reports_whether_the_share_existed(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        self.assertTrue(self.freigaben.loeschen(token))
        self.assertFalse(self.freigaben.loeschen(token))

    def test_the_index_survives_a_restart(self):
        token, _ = self.freigaben.anlegen(MAPPE)
        wieder = Freigaben(Path(self.verzeichnis.name), tage=30)
        self.assertEqual("BRAND K.", wieder.lesen(token)[0]["alarme"][0]["stichwort"])


class GemeinsamArbeitenTest(unittest.TestCase):
    def setUp(self):
        self.verzeichnis = tempfile.TemporaryDirectory()
        self.freigaben = Freigaben(Path(self.verzeichnis.name), tage=30)
        self.token, _ = self.freigaben.anlegen(MAPPE)
        self.basis = self.freigaben.stand(self.token, 0)["stand"]

    def tearDown(self):
        self.verzeichnis.cleanup()

    def schreiben(self, wer, seit, *aenderungen):
        return self.freigaben.schreiben(self.token, list(aenderungen), wer, seit)

    def mappe(self):
        return self.freigaben.lesen(self.token)[0]

    def test_two_people_editing_different_fields_both_keep_their_change(self):
        self.schreiben("anna", self.basis,
                       {"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"})
        self.schreiben("ben", self.basis,
                       {"pfad": pfad("alarme", "a1", "anrufer"), "wert": "Ben"})
        alarm = self.mappe()["alarme"][0]
        self.assertEqual("TH 2", alarm["stichwort"])
        self.assertEqual("Ben", alarm["anrufer"])

    def test_a_writer_is_told_what_the_other_one_did(self):
        self.schreiben("anna", self.basis,
                       {"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"})
        antwort = self.schreiben("ben", self.basis,
                                 {"pfad": pfad("alarme", "a1", "anrufer"), "wert": "Ben"})
        pfade = {a["pfad"] for a in antwort["aenderungen"]}
        self.assertIn(pfad("alarme", "a1", "stichwort"), pfade)

    def test_asking_again_with_the_new_revision_returns_nothing(self):
        antwort = self.schreiben("anna", self.basis,
                                 {"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"})
        self.assertEqual([], self.freigaben.stand(self.token, antwort["stand"])["aenderungen"])

    def test_the_revision_only_moves_when_something_was_written(self):
        vorher = self.freigaben.stand(self.token, 0)["stand"]
        self.assertEqual(vorher, self.schreiben("anna", vorher)["stand"])

    def test_a_deletion_reaches_the_other_side(self):
        self.schreiben("anna", self.basis, {"pfad": pfad("alarme", "a1"), "weg": True})
        self.assertEqual([], self.mappe()["alarme"])

    def test_writes_survive_a_restart(self):
        self.schreiben("anna", self.basis,
                       {"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"})
        wieder = Freigaben(Path(self.verzeichnis.name), tage=30)
        self.assertEqual("TH 2", wieder.lesen(self.token)[0]["alarme"][0]["stichwort"])

    def test_concurrent_writers_do_not_lose_each_other(self):
        """
        Twenty threads, each writing its own field of the same Alarm. Every one of them has to be
        in the document at the end - that is the whole promise of the merge.
        """
        import threading

        def schreibt(nummer):
            self.schreiben(f"person{nummer}", self.basis,
                           {"pfad": pfad("alarme", "a1", f"feld{nummer}"), "wert": nummer})

        faeden = [threading.Thread(target=schreibt, args=(i,)) for i in range(20)]
        for faden in faeden:
            faden.start()
        for faden in faeden:
            faden.join()

        alarm = self.mappe()["alarme"][0]
        self.assertEqual({i: i for i in range(20)},
                         {i: alarm.get(f"feld{i}") for i in range(20)})

    def test_a_half_written_file_never_replaces_a_readable_one(self):
        """The document is written beside the target and moved into place."""
        self.schreiben("anna", self.basis,
                       {"pfad": pfad("alarme", "a1", "stichwort"), "wert": "TH 2"})
        uebrig = list(Path(self.verzeichnis.name).glob("*.neu"))
        self.assertEqual([], uebrig)


if __name__ == "__main__":
    unittest.main()
