import shutil
import unittest

from data.ablaufplan import SPALTEN_JE_BLATT, plandaten
from data.typst import RenderError, render_plan
from entities.alarm import Arbeitsmappe
from entities.planung import Materialposten
from web.settings import settings

MAPPE = {
    "version": 1,
    "alarme": [],
    "kataloge": {
        "fahrzeuge": [
            {"id": "f-lhf", "funkrufname": "LHF 6501.3", "plaetze": "6", "fuehrerschein": "C"},
            {"id": "f-mtf", "funkrufname": "MTF 6502.1", "plaetze": "8", "fuehrerschein": "B"},
        ],
        "orte": [{"id": "o-nord", "name": "Wache Nord"},
                 {"id": "o-kita", "name": "Kindergarten",
                  "adresse": {"strasse": "Archenholdstraße", "hnr": "21", "plz": "10315",
                              "ort": "Berlin"}}],
        "tage": [{"id": "t1", "datum": "2026-09-19", "name": "Übungstag"}],
        "personen": [
            {"id": "p-alex", "name": "Alex", "anzahl": 1, "rollen": ["Ausbilder"]},
            {"id": "p-maria", "name": "Maria", "anzahl": 1},
            {"id": "p-mimen", "name": "Mimen", "anzahl": 4, "rollen": ["Mime"]},
        ],
    },
    "planung": {
        "aktiv": True,
        "programmpunkte": [{"id": "g-brand", "name": "Brand im Kindergarten"},
                           {"id": "g-leer", "name": "Rea"}],
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


def kette(*schritte) -> dict:
    """Eine Arbeitsmappe mit einer einzigen Fahrzeugkette — für die Ränder des Rasters."""
    return {
        "version": 1, "alarme": [],
        "kataloge": {"fahrzeuge": [{"id": "f-lhf", "funkrufname": "LHF 6501.3"}],
                     "orte": [{"id": "o-nord", "name": "Wache Nord"},
                              {"id": "o-kita", "name": "Kindergarten"}]},
        "planung": {"aktiv": True,
                    "laeufe": [{"id": "l-lhf", "fahrzeugId": "f-lhf", "schritte": [
                        {"id": f"s{nummer}", "sortierung": float(nummer), **schritt}
                        for nummer, schritt in enumerate(schritte)]}]},
    }


class RasterTest(unittest.TestCase):
    """Der Bogen rastert auf Viertelstunden, geplant wird minutengenau."""

    def bloecke(self, *schritte) -> list[dict]:
        mappe = Arbeitsmappe.model_validate(kette(*schritte))
        return plandaten(mappe)["gesamt"]["bloecke"]

    def test_eine_kurze_fahrt_faellt_nicht_durchs_raster(self):
        """Neun Minuten zwischen zwei Rasterpunkten sind trotzdem eine Fahrt."""
        zeilen = self.bloecke(
            {"art": "aufenthalt", "von": "2026-09-19T08:00", "bis": "2026-09-19T08:05",
             "ortId": "o-nord"},
            {"art": "fahrt", "von": "2026-09-19T08:05", "bis": "2026-09-19T08:14",
             "ortId": "o-kita"},
            {"art": "aufenthalt", "von": "2026-09-19T08:14", "bis": "2026-09-19T08:45",
             "ortId": "o-kita"},
        )[0]["zeilen"]
        self.assertEqual(["→ Kindergarten"], zeilen[0]["zellen"])

    def test_der_laengste_anteil_gewinnt_das_fenster(self):
        zeilen = self.bloecke(
            {"art": "aufenthalt", "von": "2026-09-19T08:00", "bis": "2026-09-19T08:11",
             "ortId": "o-nord"},
            {"art": "fahrt", "von": "2026-09-19T08:11", "bis": "2026-09-19T08:30",
             "ortId": "o-kita"},
        )[0]["zeilen"]
        self.assertEqual(["Wache Nord"], zeilen[0]["zellen"])
        self.assertEqual(["→ Kindergarten"], zeilen[1]["zellen"])

    def test_ueber_die_monatsgrenze_bleibt_es_eine_nacht(self):
        zeilen = self.bloecke(
            {"art": "aufenthalt", "von": "2026-09-30T23:00", "bis": "2026-10-01T01:00",
             "ortId": "o-nord"},
        )[0]["zeilen"]
        self.assertEqual(8, len(zeilen))
        self.assertEqual(["23:00", "00:45"], [zeilen[0]["zeit"], zeilen[-1]["zeit"]])

    def test_mehrere_tage_werden_zu_mehreren_bloecken(self):
        bloecke = self.bloecke(
            {"art": "aufenthalt", "von": "2026-09-19T08:00", "bis": "2026-09-19T09:00",
             "ortId": "o-nord"},
            {"art": "aufenthalt", "von": "2026-09-20T08:00", "bis": "2026-09-20T09:00",
             "ortId": "o-kita"},
        )
        self.assertEqual(["2026-09-19", "2026-09-20"], [block["datum"] for block in bloecke])
        self.assertEqual(["Wache Nord"], bloecke[0]["zeilen"][0]["zellen"])
        self.assertEqual(["Kindergarten"], bloecke[1]["zeilen"][0]["zellen"])

    def test_eine_kette_die_mit_einer_fahrt_beginnt(self):
        """Ohne vorigen Schritt gibt es kein Woher; die Fahrt fängt an, wo sie hinführt."""
        fahrt = Arbeitsmappe.model_validate(kette(
            {"art": "fahrt", "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30",
             "ortId": "o-kita"}))
        zeile = plandaten(fahrt)["fahrzeuge"][0]["zeilen"][0]
        self.assertEqual("Kindergarten", zeile["vonOrt"])


class BlattbreiteTest(unittest.TestCase):
    """Mehr Ketten als Spalten aufs Blatt passen: der Rest kommt auf das nächste."""

    def test_der_bogen_wird_gestueckelt(self):
        laeufe = [{"id": f"l{nummer}", "fahrzeugId": f"f{nummer}", "schritte": [
            {"id": f"s{nummer}", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T09:00", "ortId": "o1"}]}
            for nummer in range(SPALTEN_JE_BLATT + 2)]
        mappe = Arbeitsmappe.model_validate({
            "version": 1, "alarme": [], "kataloge": {"orte": [{"id": "o1", "name": "Wache"}]},
            "planung": {"aktiv": True, "laeufe": laeufe}})
        bloecke = plandaten(mappe)["gesamt"]["bloecke"]
        self.assertEqual([SPALTEN_JE_BLATT, 2], [len(block["spalten"]) for block in bloecke])
        self.assertEqual(["2026-09-19", "2026-09-19"], [block["datum"] for block in bloecke])


class ZettelTest(unittest.TestCase):
    """
    Ein Blatt muss für sich allein genügen: wer es in die Hand gedrückt bekommt, hat weder die
    Ortsliste noch den Materialschein dabei.
    """

    def blatt(self, name: str) -> dict:
        return next(blatt for blatt in daten()["personen"] if blatt["name"] == name)

    def test_die_orte_des_blattes_tragen_ihre_adresse(self):
        orte = self.blatt("Alex")["orte"]
        self.assertEqual(["Wache Nord", "Kindergarten"], [ort["name"] for ort in orte])
        kita = orte[1]
        self.assertEqual("Archenholdstraße 21, 10315 Berlin", kita["adresse"])
        self.assertIn("maps.apple.com", kita["apple"])
        self.assertIn("Archenholdstra%C3%9Fe%2021", kita["google"])

    def test_ohne_adresse_gibt_es_keinen_kartenlink(self):
        """Die Wache Nord hat in diesen Daten keine Adresse — dann steht auch kein Weg dorthin."""
        wache = self.blatt("Alex")["orte"][0]
        self.assertEqual("", wache["adresse"])
        self.assertNotIn("apple", wache)

    def zeile_mit_material(self, posten: list[Materialposten]) -> dict:
        mappe = Arbeitsmappe.model_validate(MAPPE | {
            "kataloge": MAPPE["kataloge"] | {"material": [{"id": "m1", "name": "Übungspuppe"}]}})
        for lauf in mappe.planung.laeufe:
            if lauf.fahrzeugId == "f-lhf":
                lauf.schritte[0].material = posten
                lauf.schritte[0].notiz = "Schlüssel nicht vergessen"
        return next(blatt for blatt in plandaten(mappe)["personen"]
                    if blatt["name"] == "Alex")["zeilen"][0]

    def test_material_und_notiz_stehen_in_der_zeile(self):
        zeile = self.zeile_mit_material([Materialposten(id="x", materialId="m1")])
        self.assertEqual(["Übungspuppe"], zeile["material"])
        self.assertEqual("Schlüssel nicht vergessen", zeile["notiz"])

    def test_eine_menge_steht_vor_dem_namen(self):
        """Ein Stück nennt nur seinen Namen; mehrere sagen, wie viele."""
        zeile = self.zeile_mit_material([Materialposten(id="x", materialId="m1", anzahl=4)])
        self.assertEqual(["4 × Übungspuppe"], zeile["material"])


class FahrzeitTest(unittest.TestCase):
    """
    Die geschätzte Fahrzeit steht neben der geplanten. Gerechnet wird sie wie im Browser; dass
    beide Seiten dasselbe herausbekommen, hält `tools/plan_vergleichen` fest.
    """

    PUNKTE = {"o-nord": {"ostwert": 400000, "nordwert": 5818000},
              "o-kita": {"ostwert": 400000, "nordwert": 5814000}}

    def zeilen(self, punkte: dict | None = None) -> list[dict]:
        mappe = Arbeitsmappe.model_validate(MAPPE)
        return plandaten(mappe, punkte)["fahrzeuge"][0]["zeilen"]

    def test_vier_kilometer_im_fahrzeug_sind_zehn_minuten(self):
        fahrt = next(zeile for zeile in self.zeilen(self.PUNKTE) if zeile["art"] == "fahrt")
        self.assertEqual(10, fahrt["geschaetzt"])

    def test_ein_aufenthalt_wird_nicht_geschaetzt(self):
        stehend = next(zeile for zeile in self.zeilen(self.PUNKTE)
                       if zeile["art"] == "aufenthalt")
        self.assertIsNone(stehend["geschaetzt"])

    def test_ohne_koordinaten_gibt_es_keine_schaetzung(self):
        self.assertTrue(all(zeile["geschaetzt"] is None for zeile in self.zeilen()))


class AnfahrtTest(unittest.TestCase):
    """
    Folgt ein Aufenthalt direkt auf einen anderen an einem anderen Ort, entsteht die Fahrt
    dazwischen von selbst. Sie beginnt mit dem Aufenthalt — er ist der Aufbruch, nicht die
    Ankunft.
    """

    PUNKTE = {"o-nord": {"ostwert": 400000, "nordwert": 5818000},
              "o-kita": {"ostwert": 400000, "nordwert": 5814000}}

    def zeilen(self, **schrittfelder) -> list[dict]:
        kette = {"id": "l-mtf", "fahrzeugId": "f-mtf", "schritte": [
            {"id": "a1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T07:00", "bis": "2026-09-19T07:50", "ortId": "o-nord",
             "besatzung": [{"id": "c1", "personId": "p-alex", "faehrt": True}]},
            {"id": "a2", "sortierung": 1.0, "art": "aufenthalt",
             "von": "2026-09-19T07:50", "bis": "2026-09-19T09:00", "ortId": "o-kita",
             "programmpunktId": "g-brand",
             "besatzung": [{"id": "c2", "personId": "p-alex", "faehrt": True}],
             **schrittfelder},
        ]}
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"planung": MAPPE["planung"] | {"laeufe": [kette]}})
        blatt = next(blatt for blatt in plandaten(mappe, self.PUNKTE)["fahrzeuge"]
                     if blatt["name"] == "MTF 6502.1")
        return blatt["zeilen"]

    def test_die_fahrt_steht_als_eigene_zeile(self):
        arten = [(zeile["art"], zeile["von"], zeile["bis"]) for zeile in self.zeilen()]
        self.assertEqual([("aufenthalt", "07:00", "07:50"),
                          ("fahrt", "07:50", "08:00"),
                          ("aufenthalt", "08:00", "09:00")], arten)

    def test_eine_eigene_fahrzeit_schlaegt_die_schaetzung(self):
        arten = [(zeile["art"], zeile["von"]) for zeile in self.zeilen(fahrzeit=25)]
        self.assertEqual([("aufenthalt", "07:00"), ("fahrt", "07:50"), ("aufenthalt", "08:15")],
                         arten)

    def test_ohne_ortswechsel_entsteht_nichts(self):
        arten = [zeile["art"] for zeile in self.zeilen(ortId="o-nord")]
        self.assertEqual(["aufenthalt", "aufenthalt"], arten)

    def test_wer_schon_am_ziel_steht_faehrt_nicht_mit(self):
        """Der Mime wartet am Kindergarten; auf seinem Blatt steht keine Anfahrt."""
        kette = {"id": "l-mtf", "fahrzeugId": "f-mtf", "schritte": [
            {"id": "a1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T07:00", "bis": "2026-09-19T07:50", "ortId": "o-nord",
             "besatzung": [{"id": "c1", "personId": "p-alex", "faehrt": True}]},
            {"id": "a2", "sortierung": 1.0, "art": "aufenthalt",
             "von": "2026-09-19T07:50", "bis": "2026-09-19T09:00", "ortId": "o-kita",
             "besatzung": [{"id": "c2", "personId": "p-alex", "faehrt": True},
                           {"id": "c3", "personId": "p-mimen"}]},
        ]}
        wartend = {"id": "l-mimen", "personId": "p-mimen", "schritte": [
            {"id": "a3", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T06:00", "bis": "2026-09-19T07:50", "ortId": "o-kita"}]}
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"planung": MAPPE["planung"] | {"laeufe": [kette, wartend]}})
        blaetter = {blatt["name"]: blatt for blatt in plandaten(mappe, self.PUNKTE)["personen"]}
        self.assertEqual(["fahrt"],
                         [zeile["art"] for zeile in blaetter["Alex"]["zeilen"]
                          if zeile["art"] == "fahrt"])
        self.assertEqual([], [zeile["art"] for zeile in blaetter["Mimen"]["zeilen"]
                              if zeile["art"] == "fahrt"])
        self.assertEqual(["06:00", "07:50"],
                         [zeile["von"] for zeile in blaetter["Mimen"]["zeilen"]])


class BewegungTest(unittest.TestCase):
    """Das Bild, das der Bildschirm auch zeichnet: Bänder, Reihen darin, Zeitfenster."""

    def bild(self, mappe: dict, modus: str = "fahrzeuge") -> list[dict]:
        return [eintrag for eintrag in plandaten(Arbeitsmappe.model_validate(mappe))["bewegung"]
                if eintrag["modus"] == modus]

    def test_jeder_ort_ein_band_in_der_reihenfolge_der_stammdaten(self):
        bilder = self.bild(MAPPE)
        self.assertEqual(1, len(bilder))
        self.assertEqual(["Wache Nord", "Kindergarten"],
                         [band["name"] for band in bilder[0]["baender"]])

    def test_das_fenster_liegt_auf_vollen_stunden(self):
        bild = self.bild(MAPPE)[0]
        self.assertEqual((480, 600), (bild["von"], bild["bis"]))

    def test_was_gleichzeitig_dasteht_bekommt_eigene_reihen(self):
        """Die Mimen stehen ab acht am Kindergarten, das LHF kommt dazu — also zwei Reihen."""
        bild = self.bild(MAPPE)[0]
        kita = next(band for band in bild["baender"] if band["name"] == "Kindergarten")
        self.assertEqual(2, kita["reihen"])
        self.assertEqual([0, 1], sorted(balken["reihe"] for balken in bild["balken"]
                                        if balken["ortId"] == "o-kita"))

    def test_eine_fahrt_verbindet_die_reihen(self):
        linie = next(eintrag for eintrag in self.bild(MAPPE)[0]["linien"]
                     if eintrag["name"] == "LHF 6501.3")
        self.assertEqual(("o-nord", "o-kita"), (linie["vonOrtId"], linie["nachOrtId"]))
        self.assertEqual((0, 1), (linie["vonReihe"], linie["nachReihe"]))

    def test_ein_ort_ohne_geschehen_bekommt_kein_band(self):
        ohne = kette({"art": "aufenthalt", "von": "2026-09-19T08:00",
                      "bis": "2026-09-19T09:00", "ortId": "o-nord"})
        self.assertEqual(["Wache Nord"],
                         [band["name"] for band in self.bild(ohne)[0]["baender"]])

    def test_das_personenbild_erzaehlt_denselben_tag_je_person(self):
        """Alex sitzt im LHF; im Personenbild ist er die Spur und das Fahrzeug die Begleitung."""
        bild = self.bild(MAPPE, "personen")[0]
        alex = [balken for balken in bild["balken"] if balken["name"] == "Alex"]
        self.assertEqual(2, len(alex))
        self.assertEqual([["LHF 6501.3"], ["LHF 6501.3"]],
                         [balken["begleitung"] for balken in alex])
        self.assertEqual(["Mimen"], [balken["name"] for balken in bild["balken"]
                                     if balken["begleitung"] == []])

    def test_jeder_tag_bekommt_sein_bild(self):
        zwei = kette(
            {"art": "aufenthalt", "von": "2026-09-19T08:00", "bis": "2026-09-19T09:00",
             "ortId": "o-nord"},
            {"art": "aufenthalt", "von": "2026-09-20T08:00", "bis": "2026-09-20T09:00",
             "ortId": "o-kita"})
        bilder = self.bild(zwei)
        self.assertEqual(["2026-09-19", "2026-09-20"], [bild["datum"] for bild in bilder])
        self.assertEqual(["Wache Nord", "Kindergarten"],
                         [band["name"] for band in bilder[1]["baender"]])

    def test_die_minuten_zaehlen_vom_tag_des_bildes(self):
        """Über Mitternacht hinaus wird die Achse länger, nicht kürzer."""
        nacht = kette({"art": "aufenthalt", "von": "2026-09-19T23:00",
                       "bis": "2026-09-20T01:00", "ortId": "o-nord"})
        bild = self.bild(nacht)[0]
        self.assertEqual((1380, 1500), (bild["von"], bild["bis"]))


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
