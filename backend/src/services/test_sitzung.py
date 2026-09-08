import shutil
import unittest

from fastapi.testclient import TestClient

from main import app
from services.sitzung import COOKIE, sitzungen
from web.settings import settings

MAPPE = {"version": 1, "alarme": [{"id": "a1", "stichwort": "BRAND K."}]}


class SitzungTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.addCleanup(self.aufraeumen)

    @staticmethod
    def aufraeumen():
        shutil.rmtree(settings.sitzung_verzeichnis, ignore_errors=True)
        settings.sitzung_verzeichnis.mkdir(parents=True, exist_ok=True)

    def anlegen(self, mappe=None) -> dict:
        antwort = self.client.post("/api/sitzung", json=mappe or MAPPE)
        self.assertEqual(200, antwort.status_code, antwort.text)
        return antwort.json()

    def test_anlegen_setzt_das_cookie_und_die_sitzung_ist_danach_die_laufende(self):
        angelegt = self.anlegen()
        self.assertEqual(angelegt["token"], self.client.cookies.get(COOKIE))
        laufende = self.client.get("/api/sitzung").json()
        self.assertEqual(angelegt["token"], laufende["token"])
        self.assertEqual("BRAND K.", laufende["arbeitsmappe"]["alarme"][0]["stichwort"])

    def test_ohne_cookie_gibt_es_keine_laufende_sitzung(self):
        self.client.cookies.clear()
        self.assertEqual(404, self.client.get("/api/sitzung").status_code)

    def test_eine_leere_sitzung_ist_erlaubt(self):
        """Eine neue Sitzung fängt bei nichts an — das war bei den Freigaben noch ein Fehler."""
        self.assertEqual(200, self.client.post("/api/sitzung", json={"alarme": []}).status_code)

    def test_wechseln_setzt_das_cookie_auf_die_andere_sitzung(self):
        erste = self.anlegen()
        zweite = self.anlegen({"version": 1, "alarme": [{"id": "b1", "stichwort": "TH 1"}]})
        self.assertEqual(zweite["token"], self.client.cookies.get(COOKIE))

        self.client.post(f"/api/sitzung/{erste['token']}/uebernehmen")
        self.assertEqual(erste["token"], self.client.cookies.get(COOKIE))
        self.assertEqual("BRAND K.",
                         self.client.get("/api/sitzung").json()["arbeitsmappe"]["alarme"][0]["stichwort"])

    def test_eine_fremde_sitzung_laesst_sich_lesen_ohne_zu_wechseln(self):
        erste = self.anlegen()
        self.anlegen({"version": 1, "alarme": []})
        gelesen = self.client.get(f"/api/sitzung/{erste['token']}").json()
        self.assertEqual("BRAND K.", gelesen["arbeitsmappe"]["alarme"][0]["stichwort"])
        self.assertNotEqual(erste["token"], self.client.cookies.get(COOKIE))

    def test_eine_geloeschte_sitzung_gibt_es_nicht_mehr(self):
        angelegt = self.anlegen()
        self.assertTrue(self.client.delete(f"/api/sitzung/{angelegt['token']}").json()["geloescht"])
        self.assertEqual(404, self.client.get(f"/api/sitzung/{angelegt['token']}").status_code)

    def test_aenderungen_gehen_hin_und_zurueck(self):
        angelegt = self.anlegen()
        token = angelegt["token"]
        stand = self.client.get(f"/api/sitzung/{token}/aenderungen").json()["stand"]
        pfad = "alarme\x1fa1\x1fstichwort"
        antwort = self.client.post(f"/api/sitzung/{token}/aenderungen", json={
            "seit": stand, "wer": "Nora",
            "aenderungen": [{"pfad": pfad, "wert": "TH 3"}]}).json()
        self.assertGreater(antwort["stand"], stand)
        gelesen = self.client.get(f"/api/sitzung/{token}").json()
        self.assertEqual("TH 3", gelesen["arbeitsmappe"]["alarme"][0]["stichwort"])


class CacheTest(unittest.TestCase):
    """Der Speicher ist ein Cache: Verdrängen darf nie Daten kosten."""

    def setUp(self):
        self.addCleanup(SitzungTest.aufraeumen)

    def test_verdraengt_wird_nach_zahl_und_die_sitzung_bleibt_lesbar(self):
        laden = sitzungen.__class__(settings.sitzung_verzeichnis, 30,
                                    cache_eintraege=2, cache_minuten=30)
        tokens = [laden.anlegen({"version": 1, "alarme": [{"id": f"a{i}"}]})[0] for i in range(4)]
        self.assertEqual(2, laden.im_speicher())
        # Die zuerst angelegte ist längst aus dem Speicher — und trotzdem vollständig da.
        self.assertEqual("a0", laden.lesen(tokens[0])[0]["alarme"][0]["id"])

    def test_verdraengt_wird_nach_zeit(self):
        laden = sitzungen.__class__(settings.sitzung_verzeichnis, 30,
                                    cache_eintraege=64, cache_minuten=0)
        token, _ = laden.anlegen({"version": 1, "alarme": []})
        laden._verdraengen()
        self.assertEqual(0, laden.im_speicher())
        self.assertEqual([], laden.lesen(token)[0]["alarme"])


class UmbenennenTest(unittest.TestCase):
    """Die Tabelle hieß einmal `freigaben`; eine laufende Installation darf nichts verlieren."""

    def setUp(self):
        self.addCleanup(SitzungTest.aufraeumen)
        SitzungTest.aufraeumen()

    def test_zeilen_der_alten_tabelle_ueberleben(self):
        import json
        import sqlite3

        verzeichnis = settings.sitzung_verzeichnis
        verzeichnis.mkdir(parents=True, exist_ok=True)
        (verzeichnis / "alt.json").write_text(
            json.dumps({"eintraege": {}, "stand": 0}), encoding="utf-8")
        db = sqlite3.connect(verzeichnis / "freigaben.sqlite")
        db.executescript("""
            CREATE TABLE freigaben (token TEXT PRIMARY KEY, angelegt TEXT NOT NULL,
                                    zuletzt TEXT NOT NULL, alarme INTEGER DEFAULT 0,
                                    bytes INTEGER DEFAULT 0);
        """)
        db.execute("INSERT INTO freigaben VALUES ('alt', '2026-09-01', '2026-09-09', 1, 10)")
        db.commit()
        db.close()

        laden = sitzungen.__class__(verzeichnis, 30)
        self.assertEqual(1, laden.anzahl())
        self.assertEqual([], laden.lesen("alt")[0]["alarme"])
