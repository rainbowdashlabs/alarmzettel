import shutil
import unittest

from data.ablaufplan import SPALTEN_JE_BLATT, plandaten
from data.fahrzeit import schaetzung
from data.typst import RenderError, plan_blattweise, render_plan
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
        zeilen = {zeile["zeit"]: [zelle["text"] for zelle in zeile["zellen"]]
                  for zeile in daten()["gesamt"]["bloecke"][0]["zeilen"]}
        self.assertEqual(["Wache Nord", "Brand im Kindergarten"], zeilen["08:00"])
        self.assertEqual(["→ Kindergarten", "Brand im Kindergarten"], zeilen["08:30"])
        self.assertEqual(["Brand im Kindergarten", "→ Wache Nord (zu Fuß)"], zeilen["09:15"])
        self.assertEqual(["Brand im Kindergarten", ""], zeilen["09:45"])

    def test_die_zelle_sagt_auch_ihre_art(self):
        """Daran hängt die Farbe auf dem Bogen: Einsatz, Fahrt oder bloßes Dastehen."""
        zeilen = {zeile["zeit"]: [zelle["art"] for zelle in zeile["zellen"]]
                  for zeile in daten()["gesamt"]["bloecke"][0]["zeilen"]}
        self.assertEqual(["aufenthalt", "einsatz"], zeilen["08:00"])
        self.assertEqual(["fahrt", "einsatz"], zeilen["08:30"])
        self.assertEqual(["einsatz", "fahrt"], zeilen["09:15"])
        self.assertEqual(["einsatz", ""], zeilen["09:45"])


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
        self.assertEqual(["→ Kindergarten"], [zelle["text"] for zelle in zeilen[0]["zellen"]])

    def test_der_laengste_anteil_gewinnt_das_fenster(self):
        zeilen = self.bloecke(
            {"art": "aufenthalt", "von": "2026-09-19T08:00", "bis": "2026-09-19T08:11",
             "ortId": "o-nord"},
            {"art": "fahrt", "von": "2026-09-19T08:11", "bis": "2026-09-19T08:30",
             "ortId": "o-kita"},
        )[0]["zeilen"]
        self.assertEqual(["Wache Nord"], [zelle["text"] for zelle in zeilen[0]["zellen"]])
        self.assertEqual(["→ Kindergarten"], [zelle["text"] for zelle in zeilen[1]["zellen"]])

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
        self.assertEqual(["Wache Nord"],
                         [zelle["text"] for zelle in bloecke[0]["zeilen"][0]["zellen"]])
        self.assertEqual(["Kindergarten"],
                         [zelle["text"] for zelle in bloecke[1]["zeilen"][0]["zellen"]])

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

    def test_jedes_blatt_zeigt_auf_seine_lese_ansicht(self):
        """
        Das Kennmuster im Kopf führt vom Papier auf den laufenden Stand — je Blatt auf seines,
        nicht auf die ganze Sitzung.
        """
        plan = plandaten(Arbeitsmappe.model_validate(MAPPE),
                         blattbasis="https://zettel.example/blatt/LESE")
        self.assertEqual("https://zettel.example/blatt/LESE/person/p-alex",
                         plan["personen"][0]["link"])
        self.assertEqual("https://zettel.example/blatt/LESE/fahrzeug/f-lhf",
                         plan["fahrzeuge"][0]["link"])

    def test_ohne_basis_traegt_das_blatt_keinen_link(self):
        """Wer ohne Sitzung druckt, bekommt einen Zettel ohne Kennmuster statt gar keinen."""
        self.assertEqual("", daten()["personen"][0]["link"])

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

    def test_zwei_orte_auf_demselben_punkt_sind_kein_weg(self):
        """Dieselbe Adresse unter zwei Namen: der Browser rechnet hier ebenfalls nichts."""
        derselbe = {"ostwert": 400000, "nordwert": 5818000}
        self.assertIsNone(schaetzung(derselbe, dict(derselbe), "fahrzeug"))

    def test_gerundet_wird_von_der_haelfte_weg(self):
        """7,5 km im Fahrzeug sind 22,5 Minuten — 25, wie `Math.round` im Browser."""
        self.assertEqual(25, schaetzung({"ostwert": 0, "nordwert": 0},
                                        {"ostwert": 0, "nordwert": 7500}, "fahrzeug"))


class OhneBlattTest(unittest.TestCase):
    """
    Wer den Tag ohnehin im Fahrzeug verbringt, braucht keinen zweiten Zettel mit demselben
    Inhalt. Er steht weiter in jeder Besatzung und im Bewegungsbild — nur sein Blatt entfällt.
    """

    def blaetter(self, **person) -> list[str]:
        personen = [eintrag | person if eintrag["id"] == "p-mimen" else eintrag
                    for eintrag in MAPPE["kataloge"]["personen"]]
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"kataloge": MAPPE["kataloge"] | {"personen": personen}})
        return [blatt["name"] for blatt in plandaten(mappe)["personen"]]

    def test_ohne_eigenes_blatt_faellt_es_weg(self):
        self.assertEqual(["Alex", "Maria"], self.blaetter(blatt=False))

    def test_vorgabe_ist_ein_blatt_fuer_jeden(self):
        self.assertEqual(["Alex", "Maria", "Mimen"], self.blaetter())

    def test_die_besatzung_bleibt_vollstaendig(self):
        personen = [eintrag | {"blatt": False} if eintrag["id"] == "p-mimen" else eintrag
                    for eintrag in MAPPE["kataloge"]["personen"]]
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"kataloge": MAPPE["kataloge"] | {"personen": personen}})
        daten = plandaten(mappe)
        namen = {platz["name"] for blatt in daten["fahrzeuge"] for zeile in blatt["zeilen"]
                 for platz in zeile["besatzung"]}
        self.assertIn("Maria", namen)


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


class RenderTest(unittest.TestCase):
    def test_ein_leerer_plan_wird_abgelehnt(self):
        leer = Arbeitsmappe.model_validate({"version": 1, "alarme": [], "kataloge": {}})
        with self.assertRaises(RenderError):
            render_plan(plandaten(leer))

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_der_plan_wird_zu_einem_pdf(self):
        pdf = render_plan(daten())
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_blattweise_gibt_je_blatt_ein_dokument(self):
        teile = dict(plan_blattweise(daten()))
        self.assertEqual(
            ["person-Alex.pdf", "person-Maria.pdf", "person-Mimen.pdf",
             "fahrzeug-LHF-6501.3.pdf", "gesamtplan.pdf"],
            list(teile))
        self.assertEqual(["Alex"],
                         [blatt["name"] for blatt in teile["person-Alex.pdf"]["personen"]])
        self.assertEqual([], teile["person-Alex.pdf"]["fahrzeuge"])
        self.assertEqual([], teile["gesamtplan.pdf"]["personen"])
        self.assertTrue(teile["gesamtplan.pdf"]["gesamt"]["bloecke"])

    @unittest.skipIf(shutil.which(settings.typst_binary) is None, "typst nicht installiert")
    def test_jedes_einzelblatt_wird_ein_pdf(self):
        for name, teil in plan_blattweise(daten()):
            with self.subTest(name=name):
                self.assertTrue(render_plan(teil).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()


class EinsatzAmOrtTest(unittest.TestCase):
    """
    Wer mit einem Fahrzeug an einen Ort gefahren wird, das mit dem Szenario nichts zu tun hat,
    soll auf seinem Zettel trotzdem lesen, was dort läuft.
    """

    def blatt(self, **schrittfelder) -> list[dict]:
        bringer = {"id": "l-mtf", "fahrzeugId": "f-mtf", "schritte": [
            {"id": "b1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T11:00", "ortId": "o-kita",
             "aufgebot": False,
             "besatzung": [{"id": "c1", "personId": "p-mimen"}], **schrittfelder}]}
        einsatz = {"id": "l-lhf", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "e1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T09:00", "bis": "2026-09-19T10:00", "ortId": "o-kita",
             "programmpunktId": "g-brand",
             "besatzung": [{"id": "c2", "personId": "p-alex", "faehrt": True}]}]}
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"planung": MAPPE["planung"] | {"laeufe": [bringer, einsatz]}})
        blatt = next(blatt for blatt in plandaten(mappe)["personen"]
                     if blatt["name"] == "Mimen")
        return blatt["zeilen"]

    def test_der_einsatz_steht_als_eigene_zeile(self):
        zeilen = self.blatt()
        self.assertEqual(["aufenthalt", "einsatz"], [zeile["art"] for zeile in zeilen])
        einsatz = zeilen[1]
        self.assertEqual(("09:00", "10:00"), (einsatz["von"], einsatz["bis"]))
        self.assertEqual("Brand im Kindergarten", einsatz["was"])
        self.assertEqual("LHF 6501.3", einsatz["fahrzeug"])

    def test_wer_selbst_dazugehoert_liest_es_nicht_zweimal(self):
        self.assertEqual(["aufenthalt"],
                         [zeile["art"] for zeile in self.blatt(programmpunktId="g-brand")])

    def test_woanders_zaehlt_nicht(self):
        self.assertEqual(["aufenthalt"], [zeile["art"] for zeile in self.blatt(ortId="o-nord")])
