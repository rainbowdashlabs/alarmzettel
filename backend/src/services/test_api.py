import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from data.sitzung import Sitzungen
from main import app
from services import sitzung as sitzungsdienst
from services.sitzung import COOKIE
from web.settings import settings

ALARM = {"id": "a1", "stichwort": "BRAND K.", "kurzinfo": "Brand im Freien",
         "einsatzmittel": [{"gruppe": "keine Gruppe",
                            "fahrzeuge": [{"funkrufname": "LHF 0001.1", "ezp": "6"}]}]}


class ApiTest(unittest.TestCase):
    """Gerendert wird, was die laufende Sitzung hält — hochgeladen wird nichts mehr."""

    @classmethod
    def setUpClass(cls):
        """
        Die Tests bekommen ihren eigenen Sitzungsspeicher. Sonst räumten sie das Verzeichnis der
        laufenden Installation ab — und wer nebenher im Browser arbeitet, verlöre seine Sitzung.
        """
        cls.ablage = tempfile.TemporaryDirectory()
        cls.vorher = sitzungsdienst.sitzungen
        sitzungsdienst.sitzungen = Sitzungen(Path(cls.ablage.name), 30)
        cls.addClassCleanup(cls.zurueckstellen)

    @classmethod
    def zurueckstellen(cls):
        sitzungsdienst.sitzungen = cls.vorher
        cls.ablage.cleanup()

    def setUp(self):
        self.client = TestClient(app)

    def sitzung(self, alarme=None):
        antwort = self.client.post(
            "/api/sitzung",
            json={"version": 1, "alarme": alarme if alarme is not None else [ALARM]})
        self.assertEqual(200, antwort.status_code, antwort.text)
        return antwort.json()

    def test_health_reports_ok(self):
        self.assertEqual("ok", self.client.get("/api/health").json()["status"])

    def test_rendering_without_a_session_is_refused(self):
        self.client.cookies.clear()
        self.assertEqual(401, self.client.post("/api/render").status_code)

    def test_rendering_an_empty_session_is_refused(self):
        self.sitzung(alarme=[])
        self.assertEqual(422, self.client.post("/api/render").status_code)

    def test_rendering_an_unknown_alarm_is_not_found(self):
        self.sitzung()
        self.assertEqual(404, self.client.post("/api/render/nope").status_code)

    def test_a_deleted_session_cannot_be_rendered(self):
        angelegt = self.sitzung()
        self.client.delete(f"/api/sitzung/{angelegt['token']}")
        self.assertEqual(404, self.client.post("/api/render").status_code)

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_render_returns_a_pdf(self):
        self.sitzung([ALARM, dict(ALARM, id="a2")])
        response = self.client.post("/api/render")
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/pdf", response.headers["content-type"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_single_alarm_render_returns_a_pdf(self):
        self.sitzung()
        response = self.client.post("/api/render/a1")
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.content.startswith(b"%PDF"))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_render_leaves_no_scratch_behind(self):
        self.sitzung()
        self.client.post("/api/render")
        scratch = settings.render_root / "tmp"
        self.assertEqual([], [p for p in scratch.iterdir() if p.is_dir()] if scratch.is_dir() else [])

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_render_resolves_the_catalogue(self):
        """Der Katalog wird beim Rendern aufgelöst, auch wenn niemand ihn vorher hochlädt."""
        self.client.post("/api/sitzung", json={
            "version": 1,
            "alarme": [{"id": "a1", "stichwortId": "s1", "stichwort": "alt",
                        "einsatzmittel": [{"gruppe": "g", "fahrzeuge": [
                            {"vorlageId": "v1", "funkrufname": "alt"}]}]}],
            "kataloge": {"stichwoerter": [{"id": "s1", "text": "BRAND 4"}],
                         "fahrzeuge": [{"id": "v1", "funkrufname": "LHF 6501.3",
                                        "staerke": "6", "ezp": "6", "status": "R2(A1)"}]}})
        self.assertEqual(200, self.client.post("/api/render").status_code)

    def test_the_link_is_the_only_credential(self):
        """Ein frischer Browser ohne Cookie darf eine Sitzung über ihren Link öffnen."""
        token = self.sitzung()["token"]
        frisch = TestClient(app)
        self.assertEqual(200, frisch.get(f"/api/sitzung/{token}").status_code)
        self.assertIsNone(frisch.cookies.get(COOKIE))


class LesetokenTest(ApiTest):
    """
    Ein Lesetoken führt auf dieselbe Sitzung und darf nur ansehen. Die Grenze liegt hier und
    nicht in der Oberfläche.
    """

    def paar(self):
        token = self.sitzung()["token"]
        antwort = self.client.post(f"/api/sitzung/{token}/lesetoken")
        self.assertEqual(200, antwort.status_code, antwort.text)
        return token, antwort.json()["token"]

    def test_es_bleibt_bei_einem(self):
        token, lesen = self.paar()
        self.assertEqual(lesen, self.client.post(f"/api/sitzung/{token}/lesetoken").json()["token"])
        self.assertNotEqual(token, lesen)

    def test_lesen_geht_und_sagt_es(self):
        token, lesen = self.paar()
        frisch = TestClient(app)
        antwort = frisch.get(f"/api/sitzung/{lesen}")
        self.assertEqual(200, antwort.status_code)
        self.assertTrue(antwort.json()["nurLesen"])
        self.assertFalse(self.client.get(f"/api/sitzung/{token}").json()["nurLesen"])
        self.assertEqual(1, len(antwort.json()["arbeitsmappe"]["alarme"]))

    def test_abholen_geht_auch(self):
        _, lesen = self.paar()
        self.assertEqual(200, self.client.get(f"/api/sitzung/{lesen}/aenderungen").status_code)

    def test_schreiben_wird_abgewiesen(self):
        token, lesen = self.paar()
        stapel = {"seit": 0, "wer": "Gast",
                  "aenderungen": [{"pfad": "alarme\x1fa1\x1fstichwort", "wert": "Geändert"}]}
        self.assertEqual(403,
                         self.client.post(f"/api/sitzung/{lesen}/aenderungen", json=stapel).status_code)
        self.assertEqual(200,
                         self.client.post(f"/api/sitzung/{token}/aenderungen", json=stapel).status_code)

    def test_loeschen_und_weitergeben_bleiben_dem_eigentlichen_vorbehalten(self):
        _, lesen = self.paar()
        self.assertEqual(403, self.client.delete(f"/api/sitzung/{lesen}").status_code)
        self.assertEqual(403, self.client.post(f"/api/sitzung/{lesen}/lesetoken").status_code)

    def test_wer_mit_dem_lesetoken_folgt_darf_drucken(self):
        _, lesen = self.paar()
        frisch = TestClient(app)
        self.assertEqual(200, frisch.post(f"/api/sitzung/{lesen}/uebernehmen").status_code)
        self.assertTrue(frisch.get("/api/sitzung").json()["nurLesen"])
        pdf = frisch.post("/api/render")
        self.assertEqual(200, pdf.status_code, pdf.text)
        self.assertTrue(pdf.content.startswith(b"%PDF"))


PLANMAPPE = {
    "version": 1,
    "alarme": [],
    "kataloge": {
        "fahrzeuge": [{"id": "f1", "funkrufname": "LHF 6501.3"}],
        "orte": [{"id": "o1", "name": "Wache Nord"}],
        "personen": [{"id": "p1", "name": "Jörg", "anzahl": 1}],
    },
    "planung": {
        "aktiv": True,
        "laeufe": [{"id": "l1", "fahrzeugId": "f1", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30", "ortId": "o1",
             "besatzung": [{"id": "b1", "personId": "p1", "faehrt": True}]}]}],
    },
}


class BlattPdfTest(ApiTest):
    """
    Wer einen Lese-Link hat, kann seinen Zettel auch mitnehmen: dasselbe Blatt, das die Seite
    zeigt, als PDF — ohne Sitzung im Browser und ohne den Stapel aller anderen.
    """

    def lesen(self) -> str:
        token = self.sitzung_mit_plan()
        return self.client.post(f"/api/sitzung/{token}/lesetoken").json()["token"]

    def sitzung_mit_plan(self) -> str:
        antwort = self.client.post("/api/sitzung", json=PLANMAPPE)
        self.assertEqual(200, antwort.status_code, antwort.text)
        return antwort.json()["token"]

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_person_und_fahrzeug_kommen_als_pdf(self):
        lesen = self.lesen()
        frisch = TestClient(app)
        for art, kennung in (("person", "p1"), ("fahrzeug", "f1")):
            with self.subTest(art=art):
                antwort = frisch.get(f"/api/render/blatt/{lesen}/{art}/{kennung}")
                self.assertEqual(200, antwort.status_code, antwort.text)
                self.assertTrue(antwort.content.startswith(b"%PDF"))
                self.assertIn("attachment", antwort.headers["content-disposition"])

    def test_was_es_nicht_gibt_wird_nicht_gedruckt(self):
        lesen = self.lesen()
        self.assertEqual(404, self.client.get(f"/api/render/blatt/{lesen}/person/nope").status_code)
        self.assertEqual(404, self.client.get(f"/api/render/blatt/{lesen}/tier/p1").status_code)
        self.assertEqual(404, self.client.get("/api/render/blatt/kein-token/person/p1").status_code)
