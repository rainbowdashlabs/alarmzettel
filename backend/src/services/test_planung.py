import unittest

from data.dokument import TRENNER, flach, rund

STAMM = {
    "rollen": ["Ausbilder", "Mime"],
    "fahrerlaubnisse": ["B", "C"],
    "tage": [{"id": "t1", "sortierung": 0.0, "datum": "2026-09-19", "name": "Übungstag"}],
    "personen": [{"id": "p1", "sortierung": 0.0, "name": "Maria", "anzahl": 1,
                  "blatt": True, "rollen": ["Ausbilder"], "fahrerlaubnis": ["B", "C"],
                  "verfuegbar": [{"id": "v1", "sortierung": 0.0,
                                  "von": "2026-09-19T10:00", "bis": "2026-09-19T15:00"}]}],
}
"""Was die Wache dauerhaft führt, steht im Katalog — nicht im Plan des einzelnen Tages."""

PLAN = {
    "aktiv": True,
    "programmpunkte": [{"id": "g1", "sortierung": 0.0, "name": "Brand im Kindergarten",
                        "alarmId": "a1"}],
    "laeufe": [{"id": "l1", "sortierung": 0.0, "fahrzeugId": "f1", "personId": "",
                "schritte": [
                    {"id": "s1", "sortierung": 0.0, "art": "aufenthalt", "mittel": "fahrzeug",
                     "fahrzeit": 0,
                     "von": "2026-09-19T06:30", "bis": "2026-09-19T07:45", "ortId": "o1",
                     "programmpunktId": "", "aufgebot": True, "notiz": "Fahrzeugcheck",
                     "besatzung": [{"id": "b1", "sortierung": 0.0, "personId": "p1",
                                    "faehrt": True}],
                     "material": [{"id": "m1", "sortierung": 0.0, "materialId": "mat1",
                                   "anzahl": 4}]},
                    {"id": "s2", "sortierung": 1.0, "art": "fahrt", "mittel": "fahrzeug",
                     "fahrzeit": 0,
                     "von": "2026-09-19T07:45", "bis": "2026-09-19T08:00", "ortId": "o1",
                     "programmpunktId": "g1", "aufgebot": False, "notiz": "",
                     "besatzung": [{"id": "b2", "sortierung": 0.0, "personId": "p1",
                                    "faehrt": False}],
                     "material": []}]}],
}

ORTE = [{"id": "o1", "sortierung": 0.0, "name": "Wache Nord",
         "adresse": {"strasse": "Junker-Jörg-Straße", "hnr": "36", "objekt": "",
                     "plz": "10318", "ort": "Karlshorst", "koordinaten": ""}}]

MAPPE = {"version": 1, "alarme": [],
         "kataloge": {"orte": ORTE, **STAMM}, "planung": PLAN}


class VorgabeTest(unittest.TestCase):
    """Eine Arbeitsmappe, die ein Feld noch nicht kennt, bekommt seine Vorgabe — nicht ''."""

    def test_orte_aus_dem_plan_landen_im_katalog(self):
        """
        Eine Sitzung, die vor dem Umzug angelegt wurde, hat ihre Orte unter `planung`. Der alte
        Pfad behält seine Bedeutung, sonst verlöre sie sie beim ersten Lesen.
        """
        alt = {
            f"planung{TRENNER}orte{TRENNER}o1{TRENNER}name": "Kindergarten",
            f"planung{TRENNER}orte{TRENNER}o1{TRENNER}sortierung": 0.0,
            f"planung{TRENNER}orte{TRENNER}o1{TRENNER}adresse{TRENNER}strasse": "Archenholdstraße",
        }
        kataloge = rund(alt)["kataloge"]
        self.assertEqual(["Kindergarten"], [ort["name"] for ort in kataloge["orte"]])
        self.assertEqual("Archenholdstraße", kataloge["orte"][0]["adresse"]["strasse"])

    def test_ein_leerer_wahrheitswert_wird_zur_vorgabe(self):
        """
        Eine Sitzung, die vor der Erweiterung geschrieben wurde, trägt "" statt Ja oder Nein.
        Sie muss sich weiter lesen lassen, sonst kostet ein neues Feld bestehende Arbeit.
        """
        from entities.planung import Schritt

        from entities.planung import Materialposten

        self.assertIs(True, Schritt.model_validate({"aufgebot": ""}).aufgebot)
        self.assertIs(False, Schritt.model_validate({"aufgebot": False}).aufgebot)
        self.assertEqual(1, Materialposten.model_validate({"anzahl": ""}).anzahl)
        self.assertEqual(4, Materialposten.model_validate({"anzahl": 4}).anzahl)

    def test_ein_alter_schritt_gehoert_zum_aufgebot(self):
        alt = {"version": 1, "alarme": [], "kataloge": {}, "planung": {
            "aktiv": True,
            "laeufe": [{"id": "l1", "sortierung": 0.0, "fahrzeugId": "f1", "personId": "",
                        "schritte": [{"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
                                      "mittel": "fahrzeug", "von": "2026-09-19T08:00",
                                      "bis": "2026-09-19T09:00", "ortId": "o1",
                                      "programmpunktId": "g1", "besatzung": []}]}]}}
        schritt = rund(flach(alt))["planung"]["laeufe"][0]["schritte"][0]
        self.assertIs(True, schritt["aufgebot"])


class PlanungRundlaufTest(unittest.TestCase):
    """Der Plan ist das Tiefste im Dokument; flach und zurück muss er derselbe sein."""

    def rund(self) -> dict:
        return rund(flach(MAPPE))["planung"]

    def test_der_ganze_plan_kommt_unveraendert_zurueck(self):
        self.assertEqual(PLAN, self.rund())

    def test_die_kette_behaelt_ihre_reihenfolge(self):
        schritte = self.rund()["laeufe"][0]["schritte"]
        self.assertEqual(["s1", "s2"], [schritt["id"] for schritt in schritte])

    def test_die_besatzung_haengt_am_schritt(self):
        schritte = self.rund()["laeufe"][0]["schritte"]
        self.assertTrue(schritte[0]["besatzung"][0]["faehrt"])
        self.assertFalse(schritte[1]["besatzung"][0]["faehrt"])

    def test_die_stammdaten_stehen_im_katalog(self):
        """
        Orte, Tage, Personal, Rollen und Klassen gehören der Wache und überdauern den einzelnen
        Übungstag — die Ketten zeigen nur auf ihre Kennungen.
        """
        kataloge = rund(flach(MAPPE))["kataloge"]
        self.assertEqual(ORTE, kataloge["orte"])
        for name, erwartet in STAMM.items():
            self.assertEqual(erwartet, kataloge[name], name)

    def test_ohne_plan_kommt_ein_leerer_zurueck(self):
        leer = rund(flach({"version": 1, "alarme": [], "kataloge": {}}))["planung"]
        self.assertFalse(leer["aktiv"])
        self.assertEqual([], leer["laeufe"])

    def test_jeder_schritt_steht_unter_seiner_eigenen_kennung(self):
        """Zwei Leute an verschiedenen Schritten desselben Laufs dürfen sich nicht überschreiben."""
        pfade = [pfad for pfad in flach(MAPPE) if "schritte" in pfad]
        self.assertTrue(any("\x1fs1\x1f" in pfad for pfad in pfade))
        self.assertTrue(any("\x1fs2\x1f" in pfad for pfad in pfade))
