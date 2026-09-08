import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from data.adressen import SCHEMA, Adressen

WACHE = ("Junker-Jörg-Straße", 36, "", "10318", "Karlshorst", 399598.791, 5815944.114)
ZIELE = [
    ("Marksburgstraße", 28, "", "10318", "Karlshorst", 399616.4, 5816240.7),
    ("Marksburgstraße", 28, "A", "10318", "Karlshorst", 399620.0, 5816244.0),
    ("Markgrafenstraße", 1, "", "10969", "Kreuzberg", 391000.0, 5818000.0),
    ("Archenholdstraße", 21, "", "10315", "Friedrichsfelde", 398470.239, 5818552.633),
]


def _bauen(datei: Path, stand: datetime | None = None) -> None:
    datei.unlink(missing_ok=True)
    verbindung = sqlite3.connect(datei)
    verbindung.executescript(SCHEMA)
    for strasse, hnr, zusatz, plz, ort, ost, nord in [WACHE, *ZIELE]:
        verbindung.execute("INSERT INTO adressen VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (strasse, strasse.lower(), hnr, zusatz, plz, ort, ost, nord))
    verbindung.execute("INSERT INTO stand VALUES (?)",
                       ((stand or datetime.now(UTC)).isoformat(),))
    verbindung.commit()
    verbindung.close()


class AdressenTest(unittest.TestCase):
    def setUp(self):
        self.verzeichnis = tempfile.TemporaryDirectory()
        self.datei = Path(self.verzeichnis.name) / "adressen.sqlite"
        self.addCleanup(self.verzeichnis.cleanup)

    def gefuellt(self, stand: datetime | None = None) -> Adressen:
        _bauen(self.datei, stand)
        return Adressen(self.datei)

    def test_without_a_download_everything_answers_empty(self):
        leer = Adressen(self.datei)
        self.assertFalse(leer.bestand()["verfuegbar"])
        self.assertEqual([], leer.strassen("marksburg"))
        self.assertEqual([], leer.hausnummern("Marksburgstraße"))
        self.assertIsNone(leer.finden("Marksburgstraße", "28"))
        self.assertTrue(leer.veraltet())

    def test_a_fresh_copy_is_not_stale_and_an_old_one_is(self):
        self.assertFalse(self.gefuellt().veraltet())
        alt = self.gefuellt(datetime.now(UTC) - timedelta(days=31))
        self.assertTrue(alt.veraltet())

    def test_streets_are_completed_from_the_second_letter(self):
        adressen = self.gefuellt()
        self.assertEqual([], adressen.strassen("m"))
        namen = [treffer["strasse"] for treffer in adressen.strassen("mark")]
        self.assertEqual(["Markgrafenstraße", "Marksburgstraße"], namen)

    def test_a_street_reports_the_postcode_it_lies_in(self):
        treffer = self.gefuellt().strassen("archen")
        self.assertEqual(1, len(treffer))
        self.assertEqual(("10315", "Friedrichsfelde"), (treffer[0]["plz"], treffer[0]["ort"]))

    def test_a_house_number_with_a_letter_is_a_different_door(self):
        adressen = self.gefuellt()
        self.assertEqual("28", adressen.finden("Marksburgstraße", "28")["hnr"])
        self.assertEqual("28A", adressen.finden("Marksburgstraße", "28a")["hnr"])
        self.assertIsNone(adressen.finden("Marksburgstraße", "29"))

    def test_the_postcode_narrows_a_street_name_shared_by_two_places(self):
        adressen = self.gefuellt()
        self.assertIsNone(adressen.finden("Marksburgstraße", "28", "10969"))
        self.assertIsNotNone(adressen.finden("Marksburgstraße", "28", "10318"))

    def test_house_numbers_come_back_in_order(self):
        nummern = [eintrag["hnr"] for eintrag in self.gefuellt().hausnummern("Marksburgstraße")]
        self.assertEqual(["28", "28A"], nummern)

    def test_nothing_typed_at_all_is_not_a_lookup(self):
        adressen = self.gefuellt()
        self.assertIsNone(adressen.finden("Marksburgstraße", ""))
        self.assertIsNone(adressen.finden("Marksburgstraße", "A"))

    def test_the_house_number_split(self):
        self.assertEqual((28, ""), Adressen._hausnummer("28"))
        self.assertEqual((28, "A"), Adressen._hausnummer(" 28 a "))
        self.assertEqual((None, ""), Adressen._hausnummer("keine"))


class AdressenApiTest(unittest.TestCase):
    """The routes are asked on every keystroke, so none of them may fail on a missing list."""

    def setUp(self):
        from fastapi.testclient import TestClient

        import services.adressen as dienst
        from main import app

        self.verzeichnis = tempfile.TemporaryDirectory()
        self.addCleanup(self.verzeichnis.cleanup)
        self.datei = Path(self.verzeichnis.name) / "adressen.sqlite"
        vorher = dienst.adressen
        self.addCleanup(setattr, dienst, "adressen", vorher)
        self.dienst = dienst
        self.client = TestClient(app)

    def fuellen(self):
        _bauen(self.datei)
        self.dienst.adressen = Adressen(self.datei)

    def leeren(self):
        self.dienst.adressen = Adressen(self.datei)

    def test_status_says_when_there_is_nothing_to_complete_from(self):
        self.leeren()
        self.assertFalse(self.client.get("/api/adressen/status").json()["verfuegbar"])
        self.fuellen()
        self.assertTrue(self.client.get("/api/adressen/status").json()["verfuegbar"])

    def test_every_route_answers_empty_without_a_list(self):
        self.leeren()
        self.assertEqual([], self.client.get("/api/adressen/strassen?q=mark").json())
        self.assertEqual([], self.client.get(
            "/api/adressen/hausnummern?strasse=Marksburgstraße").json())
        self.assertIsNone(self.client.get(
            "/api/adressen?strasse=Marksburgstraße&hnr=28").json())

    def test_a_lookup_returns_the_official_coordinates(self):
        self.fuellen()
        punkt = self.client.get("/api/adressen?strasse=Archenholdstraße&hnr=21&plz=10315").json()
        self.assertEqual("Friedrichsfelde", punkt["ort"])
        self.assertAlmostEqual(398470.239, punkt["ostwert"], places=3)
