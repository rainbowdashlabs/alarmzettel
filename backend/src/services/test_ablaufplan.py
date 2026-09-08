import shutil
import unittest

from data.ablaufplan import plandaten
from data.typst import RenderError, render_plan
from entities.alarm import Arbeitsmappe
from web.settings import settings

MAPPE = {
    "version": 1,
    "alarme": [],
    "kataloge": {"fahrzeuge": [
        {"id": "f-lhf", "funkrufname": "LHF 6501.3", "plaetze": "6", "fuehrerschein": "C"},
        {"id": "f-mtf", "funkrufname": "MTF 6502.1", "plaetze": "8", "fuehrerschein": "B"},
    ]},
    "planung": {
        "aktiv": True,
        "tage": [{"id": "t1", "datum": "2026-09-19", "name": "Übungstag"}],
        "orte": [{"id": "o-nord", "name": "Wache Nord"},
                 {"id": "o-kita", "name": "Kindergarten"}],
        "personen": [
            {"id": "p-alex", "name": "Alex", "anzahl": 1, "rollen": ["Ausbilder"]},
            {"id": "p-maria", "name": "Maria", "anzahl": 1},
            {"id": "p-mimen", "name": "Mimen", "anzahl": 4, "rollen": ["Mime"]},
        ],
        "programmpunkte": [{"id": "g-brand", "name": "Brand im Kindergarten", "ortId": "o-kita"},
                           {"id": "g-leer", "name": "Rea", "ortId": "o-nord"}],
        "laeufe": [
            {"id": "l-lhf", "fahrzeugId": "f-lhf", "schritte": [
                {"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
                 "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30", "ortId": "o-nord",
                 "besatzung": [{"id": "b1", "personId": "p-alex", "faehrt": True},
                               {"id": "b2", "personId": "p-maria"}]},
                {"id": "s2", "sortierung": 1.0, "art": "fahrt",
                 "von": "2026-09-19T08:30", "bis": "2026-09-19T08:45", "ortId": "o-kita",
                 "besatzung": [{"id": "b3", "personId": "p-alex", "faehrt": True},
                               {"id": "b4", "personId": "p-maria"}]},
                {"id": "s3", "sortierung": 2.0, "art": "aufenthalt",
                 "von": "2026-09-19T08:45", "bis": "2026-09-19T10:00", "ortId": "o-kita",
                 "programmpunktId": "g-brand",
                 "besatzung": [{"id": "b5", "personId": "p-alex", "faehrt": True},
                               {"id": "b6", "personId": "p-maria"}]},
            ]},
            {"id": "l-mimen", "personId": "p-mimen", "schritte": [
                {"id": "s4", "sortierung": 0.0, "art": "aufenthalt",
                 "von": "2026-09-19T08:00", "bis": "2026-09-19T09:00", "ortId": "o-kita",
                 "programmpunktId": "g-brand"},
                {"id": "s5", "sortierung": 1.0, "art": "fahrt", "mittel": "fuss",
                 "von": "2026-09-19T09:00", "bis": "2026-09-19T09:30", "ortId": "o-nord"},
            ]},
        ],
    },
}


def daten() -> dict:
    return plandaten(Arbeitsmappe.model_validate(MAPPE))


class PersonenblattTest(unittest.TestCase):
    """Das Blatt einer Person wird nirgends gepflegt — es ist die Summe ihrer Schritte."""

    def blatt(self, name: str) -> dict:
        return next(blatt for blatt in daten()["personen"] if blatt["name"] == name)

    def test_alex_faehrt_das_lhf(self):
        zeilen = self.blatt("Alex")["zeilen"]
        self.assertEqual(["08:00", "08:30", "08:45"], [zeile["von"] for zeile in zeilen])
        self.assertTrue(all(zeile["faehrt"] for zeile in zeilen))
        self.assertEqual(["LHF 6501.3"] * 3, [zeile["fahrzeug"] for zeile in zeilen])

    def test_maria_sitzt_nur_mit(self):
        self.assertFalse(any(zeile["faehrt"] for zeile in self.blatt("Maria")["zeilen"]))

    def test_die_eigene_kette_zaehlt_mit(self):
        zeilen = self.blatt("Mimen")["zeilen"]
        self.assertEqual(2, len(zeilen))
        self.assertEqual("", zeilen[0]["fahrzeug"])
        self.assertEqual("→ Wache Nord", zeilen[1]["was"])

    def test_ort_und_lage_stehen_nebeneinander(self):
        letzte = self.blatt("Alex")["zeilen"][-1]
        self.assertEqual("Kindergarten", letzte["was"])
        self.assertEqual("Brand im Kindergarten", letzte["lage"])


class FahrzeugblattTest(unittest.TestCase):
    def test_nur_fahrzeuge_mit_kette(self):
        blaetter = daten()["fahrzeuge"]
        self.assertEqual(["LHF 6501.3"], [blatt["name"] for blatt in blaetter])

    def test_die_besatzung_steht_je_schritt(self):
        erste = daten()["fahrzeuge"][0]["zeilen"][0]
        self.assertEqual([("Alex", True), ("Maria", False)],
                         [(sitzt["name"], sitzt["faehrt"]) for sitzt in erste["besatzung"]])

    def test_eine_fahrt_sagt_woher_und_wohin(self):
        fahrt = daten()["fahrzeuge"][0]["zeilen"][1]
        self.assertEqual("Wache Nord", fahrt["vonOrt"])
        self.assertEqual("→ Kindergarten", fahrt["was"])


class GesamtplanTest(unittest.TestCase):
    """Das Raster, das der Plan von Hand war — erzeugt statt gepflegt, also nie abweichend."""

    def test_ein_block_je_tag_und_blattbreite(self):
        bloecke = daten()["gesamt"]["bloecke"]
        self.assertEqual(1, len(bloecke))
        self.assertEqual(["LHF 6501.3", "Mimen"],
                         [spalte["name"] for spalte in bloecke[0]["spalten"]])

    def test_das_raster_deckt_den_ganzen_tag_ab(self):
        zeilen = daten()["gesamt"]["bloecke"][0]["zeilen"]
        self.assertEqual("08:00", zeilen[0]["zeit"])
        self.assertEqual("09:45", zeilen[-1]["zeit"])
        self.assertEqual(8, len(zeilen))

    def test_eine_zelle_sagt_was_gerade_laeuft(self):
        zeilen = {zeile["zeit"]: zeile["zellen"]
                  for zeile in daten()["gesamt"]["bloecke"][0]["zeilen"]}
        self.assertEqual(["Wache Nord", "Brand im Kindergarten"], zeilen["08:00"])
        self.assertEqual(["→ Kindergarten", "Brand im Kindergarten"], zeilen["08:30"])
        self.assertEqual(["Brand im Kindergarten", "→ Wache Nord (zu Fuß)"], zeilen["09:15"])
        self.assertEqual(["Brand im Kindergarten", ""], zeilen["09:45"])


class RenderTest(unittest.TestCase):
    def test_ein_leerer_plan_wird_abgelehnt(self):
        leer = Arbeitsmappe.model_validate({"version": 1, "alarme": [], "kataloge": {}})
        with self.assertRaises(RenderError):
            render_plan(plandaten(leer))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_der_plan_wird_zu_einem_pdf(self):
        pdf = render_plan(daten())
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
