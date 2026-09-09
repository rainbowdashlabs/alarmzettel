import unittest

from data.alarmplan import ableitung, mit_plan
from data.katalog import mit_katalog
from entities.alarm import Arbeitsmappe

MAPPE = {
    "version": 1,
    "alarme": [{
        "id": "a-brand", "stichwort": "Brand M", "einsatzZeit": "07:00",
        "einsatzDatum": "01.01.2026", "meldungZeit": "06:58", "meldungDatum": "01.01.2026",
        "einsatzadresse": {"strasse": "Von Hand", "hnr": "9"},
        "einsatzmittel": [{"id": "g1", "gruppe": "1. Alarm", "fahrzeuge": []}],
    }, {
        "id": "a-frei", "stichwort": "Ohne Plan", "einsatzZeit": "12:00",
    }],
    "kataloge": {"fahrzeuge": [
        {"id": "f-lhf", "funkrufname": "LHF 6501.3", "ezp": "6", "status": "R2(A1)"},
        {"id": "f-mtf", "funkrufname": "MTF 6502.1"},
    ]},
    "planung": {
        "aktiv": True,
        "orte": [{"id": "o-nord", "name": "Wache Nord"},
                 {"id": "o-kita", "name": "Kindergarten",
                  "adresse": {"strasse": "Archenholdstraße", "hnr": "21", "plz": "10315",
                              "ort": "Berlin"}}],
        "personen": [{"id": "p-alex", "name": "Alex", "anzahl": 1},
                     {"id": "p-mimen", "name": "Mimen", "anzahl": 4}],
        "programmpunkte": [{"id": "g-brand", "name": "Brand im Kindergarten",
                            "ortId": "o-kita", "alarmId": "a-brand"}],
        "laeufe": [
            {"id": "l-lhf", "fahrzeugId": "f-lhf", "schritte": [
                {"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
                 "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30", "ortId": "o-nord",
                 "besatzung": [{"id": "b0", "personId": "p-alex", "faehrt": True}]},
                {"id": "s2", "sortierung": 1.0, "art": "fahrt",
                 "von": "2026-09-19T08:30", "bis": "2026-09-19T08:45", "ortId": "o-kita",
                 "besatzung": [{"id": "b1", "personId": "p-alex", "faehrt": True}]},
                {"id": "s3", "sortierung": 2.0, "art": "aufenthalt",
                 "von": "2026-09-19T08:45", "bis": "2026-09-19T10:00", "ortId": "o-kita",
                 "programmpunktId": "g-brand",
                 "besatzung": [{"id": "b2", "personId": "p-alex", "faehrt": True},
                               {"id": "b3", "personId": "p-mimen"}]},
            ]},
            {"id": "l-mtf", "fahrzeugId": "f-mtf", "schritte": [
                {"id": "s4", "sortierung": 0.0, "art": "aufenthalt",
                 "von": "2026-09-19T09:00", "bis": "2026-09-19T10:00", "ortId": "o-kita",
                 "programmpunktId": "g-brand",
                 "besatzung": [{"id": "b4", "personId": "p-alex", "faehrt": True}]},
            ]},
        ],
    },
}


def mappe(**aenderung) -> Arbeitsmappe:
    return Arbeitsmappe.model_validate(MAPPE | aenderung)


class BlaetterTest(unittest.TestCase):
    """Der Zettel ist an ein Fahrzeug gerichtet, also entsteht er je Fahrzeug einmal."""

    def alarme(self, **aenderung):
        return mit_plan(mappe(**aenderung)).alarme

    def test_ein_blatt_je_beteiligtem_fahrzeug(self):
        alarme = self.alarme()
        self.assertEqual(["a-brand", "a-brand", "a-frei"], [alarm.id for alarm in alarme])

    def test_der_graue_funkrufname_wechselt(self):
        grau = [[fahrzeug.funkrufname
                 for gruppe in alarm.einsatzmittel for fahrzeug in gruppe.fahrzeuge
                 if fahrzeug.alarmFuer]
                for alarm in self.alarme()[:2]]
        self.assertEqual([["LHF 6501.3"], ["MTF 6502.1"]], grau)

    def test_das_aufgebot_listet_alle(self):
        gruppe = self.alarme()[0].einsatzmittel[0]
        self.assertEqual("1. Alarm", gruppe.gruppe)
        self.assertEqual(["LHF 6501.3", "MTF 6502.1"],
                         [fahrzeug.funkrufname for fahrzeug in gruppe.fahrzeuge])

    def test_die_staerke_ist_die_tatsaechliche_besatzung(self):
        gruppe = self.alarme()[0].einsatzmittel[0]
        self.assertEqual(["5", "1"], [fahrzeug.staerke for fahrzeug in gruppe.fahrzeuge])

    def test_die_zeit_ist_der_beginn_der_anfahrt(self):
        erstes = self.alarme()[0]
        self.assertEqual(("19.09.2026", "08:30"), (erstes.einsatzDatum, erstes.einsatzZeit))
        self.assertEqual(("19.09.2026", "08:30"), (erstes.meldungDatum, erstes.meldungZeit))

    def test_wer_schon_da_steht_faehrt_nicht_an(self):
        zweites = self.alarme()[1]
        self.assertEqual("09:00", zweites.einsatzZeit)

    def test_die_einsatzadresse_kommt_vom_ort_der_lage(self):
        self.assertEqual("Archenholdstraße", self.alarme()[0].einsatzadresse.strasse)

    def test_ein_alarm_ohne_lage_bleibt_wie_er_ist(self):
        frei = self.alarme()[-1]
        self.assertEqual("12:00", frei.einsatzZeit)
        self.assertEqual([], frei.einsatzmittel)

    def test_ohne_fahrzeug_bleibt_das_getippte_aufgebot(self):
        """Sonst druckt der Zwischenstand „Lage da, Ketten noch nicht“ an niemanden adressiert."""
        ohne = {**MAPPE["planung"], "laeufe": []}
        alarme = self.alarme(planung=ohne)
        self.assertEqual(["a-brand", "a-frei"], [alarm.id for alarm in alarme])
        self.assertEqual("1. Alarm", alarme[0].einsatzmittel[0].gruppe)
        self.assertEqual("07:00", alarme[0].einsatzZeit)
        self.assertEqual("Archenholdstraße", alarme[0].einsatzadresse.strasse)

    def test_ausgeschaltete_planung_aendert_nichts(self):
        alarme = self.alarme(planung=MAPPE["planung"] | {"aktiv": False})
        self.assertEqual(["a-brand", "a-frei"], [alarm.id for alarm in alarme])
        self.assertEqual("07:00", alarme[0].einsatzZeit)
        self.assertEqual("Von Hand", alarme[0].einsatzadresse.strasse)


class AnfahrtTest(unittest.TestCase):
    """Die Einsatzzeit ist der Beginn der Anfahrt — sofern es eine gibt."""

    def zeit(self, planung: dict) -> str:
        return mit_plan(mappe(planung=planung)).alarme[0].einsatzZeit

    def test_eine_fahrt_darf_die_lage_selbst_tragen(self):
        """Zeigt schon die Anfahrt auf die Lage, ist ihr Beginn die Einsatzzeit."""
        laeufe = [{"id": "l", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30", "ortId": "o-nord"},
            {"id": "s2", "sortierung": 1.0, "art": "fahrt", "programmpunktId": "g-brand",
             "von": "2026-09-19T08:30", "bis": "2026-09-19T08:45", "ortId": "o-kita"}]}]
        self.assertEqual("08:30", self.zeit(MAPPE["planung"] | {"laeufe": laeufe}))

    def test_eine_fahrt_woanders_hin_ist_keine_anfahrt(self):
        """Der vorige Schritt zählt nur, wenn er zu diesem Ort führt."""
        laeufe = [{"id": "l", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "fahrt",
             "von": "2026-09-19T07:00", "bis": "2026-09-19T08:00", "ortId": "o-nord"},
            {"id": "s2", "sortierung": 1.0, "art": "aufenthalt", "programmpunktId": "g-brand",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T09:00", "ortId": "o-kita"}]}]
        self.assertEqual("08:00", self.zeit(MAPPE["planung"] | {"laeufe": laeufe}))

    def test_zwei_lagen_auf_denselben_alarm_nimmt_die_erste(self):
        punkte = MAPPE["planung"]["programmpunkte"] + [
            {"id": "g-zweite", "name": "Noch eine", "ortId": "o-nord", "alarmId": "a-brand"}]
        alarme = mit_plan(mappe(planung=MAPPE["planung"] | {"programmpunkte": punkte})).alarme
        self.assertEqual("Archenholdstraße", alarme[0].einsatzadresse.strasse)


class KatalogZusammenspielTest(unittest.TestCase):
    """Das Blatt entsteht vor der Katalogauflösung, also erbt es EZP, Status und Trupp."""

    def test_der_katalog_fuellt_die_abgeleiteten_fahrzeuge(self):
        gruppe = mit_katalog(mit_plan(mappe())).alarme[0].einsatzmittel[0]
        lhf = gruppe.fahrzeuge[0]
        self.assertEqual("6", lhf.ezp)
        self.assertEqual("R2(A1)", lhf.status)
        self.assertEqual("Stärke=5: SF, AT, WT", lhf.trupp)


class AbleitungTest(unittest.TestCase):
    """Was der Editor anzeigt, ist dasselbe, was gedruckt wird."""

    def test_ohne_lage_gibt_es_nichts_anzuzeigen(self):
        gelesen = mappe()
        frei = next(alarm for alarm in gelesen.alarme if alarm.id == "a-frei")
        self.assertIsNone(ableitung(gelesen, frei))

    def test_die_blaetter_stehen_mit_zeit_und_staerke(self):
        gelesen = mappe()
        alarm = next(alarm for alarm in gelesen.alarme if alarm.id == "a-brand")
        gefunden = ableitung(gelesen, alarm)
        self.assertEqual("Brand im Kindergarten", gefunden["lage"])
        self.assertEqual("Archenholdstraße", gefunden["einsatzadresse"]["strasse"])
        self.assertEqual(
            [("LHF 6501.3", "5", "08:30"), ("MTF 6502.1", "1", "09:00")],
            [(blatt["funkrufname"], blatt["staerke"], blatt["einsatzZeit"])
             for blatt in gefunden["blaetter"]])


if __name__ == "__main__":
    unittest.main()
