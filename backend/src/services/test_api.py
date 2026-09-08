import shutil
import unittest

from fastapi.testclient import TestClient

from main import app
from web.settings import settings

ALARM = {"id": "a1", "stichwort": "BRAND K.", "kurzinfo": "Brand im Freien",
         "einsatzmittel": [{"gruppe": "keine Gruppe",
                            "fahrzeuge": [{"funkrufname": "LHF 0001.1", "ezp": "6"}]}]}


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def session(self) -> dict:
        return {"X-Session-Id": self.client.post("/api/session").json()["id"]}

    def test_health_reports_ok(self):
        self.assertEqual("ok", self.client.get("/api/health").json()["status"])

    def test_session_starts_empty_and_counts_down(self):
        created = self.client.post("/api/session").json()
        self.assertLessEqual(created["secondsLeft"], settings.session_ttl_minutes * 60)
        status = self.client.get("/api/session", headers={"X-Session-Id": created["id"]}).json()
        self.assertEqual(0, status["alarme"])

    def test_request_without_session_is_rejected(self):
        self.assertEqual(401, self.client.get("/api/session").status_code)

    def test_unknown_session_is_not_found(self):
        self.assertEqual(404, self.client.get("/api/session", headers={"X-Session-Id": "x"}).status_code)

    def test_arbeitsmappe_is_stored_on_the_session(self):
        headers = self.session()
        self.client.put("/api/session/arbeitsmappe", headers=headers,
                        json={"version": 1, "alarme": [ALARM]})
        self.assertEqual(1, self.client.get("/api/session", headers=headers).json()["alarme"])

    def test_dropped_session_is_gone(self):
        headers = self.session()
        self.client.delete("/api/session", headers=headers)
        self.assertEqual(404, self.client.get("/api/session", headers=headers).status_code)

    def test_rendering_an_empty_session_is_refused(self):
        self.assertEqual(422, self.client.post("/api/render", headers=self.session()).status_code)

    def test_rendering_an_unknown_alarm_is_not_found(self):
        headers = self.session()
        self.client.put("/api/session/arbeitsmappe", headers=headers,
                        json={"version": 1, "alarme": [ALARM]})
        self.assertEqual(404, self.client.post("/api/render/nope", headers=headers).status_code)

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_render_returns_a_pdf(self):
        headers = self.session()
        self.client.put("/api/session/arbeitsmappe", headers=headers,
                        json={"version": 1, "alarme": [ALARM, dict(ALARM, id="a2")]})
        response = self.client.post("/api/render", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertEqual("application/pdf", response.headers["content-type"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_single_alarm_render_returns_a_pdf(self):
        headers = self.session()
        self.client.put("/api/session/arbeitsmappe", headers=headers,
                        json={"version": 1, "alarme": [ALARM]})
        response = self.client.post("/api/render/a1", headers=headers)
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.content.startswith(b"%PDF"))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_render_leaves_no_scratch_behind(self):
        headers = self.session()
        self.client.put("/api/session/arbeitsmappe", headers=headers,
                        json={"version": 1, "alarme": [ALARM]})
        self.client.post("/api/render", headers=headers)
        scratch = settings.render_root / "tmp"
        self.assertEqual([], [p for p in scratch.iterdir() if p.is_dir()] if scratch.is_dir() else [])


class FreigabeEndpointTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def teilen(self, alarme=None):
        return self.client.post("/api/freigabe",
                                json={"version": 1, "alarme": alarme if alarme is not None else [ALARM]})

    def test_sharing_returns_a_link_and_an_expiry(self):
        antwort = self.teilen()
        self.assertEqual(200, antwort.status_code)
        körper = antwort.json()
        self.assertIn(körper["token"], körper["url"])
        self.assertEqual(30, körper["tage"])

    def test_a_shared_working_set_reads_back(self):
        token = self.teilen().json()["token"]
        gelesen = self.client.get(f"/api/freigabe/{token}").json()
        self.assertEqual("BRAND K.", gelesen["arbeitsmappe"]["alarme"][0]["stichwort"])

    def test_sharing_nothing_is_refused(self):
        self.assertEqual(422, self.teilen(alarme=[]).status_code)

    def test_an_unknown_link_is_not_found(self):
        self.assertEqual(404, self.client.get("/api/freigabe/gibtesnicht").status_code)

    def test_a_deleted_share_is_gone(self):
        token = self.teilen().json()["token"]
        self.assertTrue(self.client.delete(f"/api/freigabe/{token}").json()["geloescht"])
        self.assertEqual(404, self.client.get(f"/api/freigabe/{token}").status_code)

    def test_a_share_needs_no_session(self):
        """The link is the only credential: opening it must work in a fresh browser."""
        token = self.teilen().json()["token"]
        frisch = TestClient(app)
        self.assertEqual(200, frisch.get(f"/api/freigabe/{token}").status_code)


if __name__ == "__main__":
    unittest.main()
