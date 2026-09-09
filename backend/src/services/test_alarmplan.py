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
    "kataloge": {
        "fahrzeuge": [
            {"id": "f-lhf", "funkrufname": "LHF 6501.3", "ezp": "6", "status": "R2(A1)"},
            {"id": "f-mtf", "funkrufname": "MTF 6502.1"},
            {"id": "f-rtw", "funkrufname": "RTW 6503.1"},
        ],
        "orte": [
            {"id": "o-nord", "name": "Wache Nord"},
            {"id": "o-kita", "name": "Kindergarten",
             "adresse": {"strasse": "Archenholdstraße", "hnr": "21", "plz": "10315",
                         "ort": "Berlin"}},
        ],
        "personen": [{"id": "p-alex", "name": "Alex", "anzahl": 1},
                     {"id": "p-mimen", "name": "Mimen", "anzahl": 4}],
    },
    "planung": {
        "aktiv": True,
        "programmpunkte": [{"id": "g-brand", "name": "Brand im Kindergarten",
                            "alarmId": "a-brand"}],
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


class GruppenTest(unittest.TestCase):
    """
    Zusammen auf einen Zettel kommt, wer zusammen alarmiert ist: wessen Zeiten sich überschneiden.
    Zwei Einsätze nacheinander an derselben Lage sind zwei Zettel.
    """

    def zettel(self, *fenster: tuple[str, str, str]) -> list[Alarm]:
        laeufe = [{"id": f"l-{nummer}", "fahrzeugId": fahrzeugId, "schritte": [
            {"id": f"s-{nummer}", "sortierung": 0.0, "art": "aufenthalt",
             "von": f"2026-09-19T{von}", "bis": f"2026-09-19T{bis}", "ortId": "o-kita",
             "programmpunktId": "g-brand",
             "besatzung": [{"id": f"b-{nummer}", "personId": "p-alex", "faehrt": True}]}]}
            for nummer, (fahrzeugId, von, bis) in enumerate(fenster)]
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"planung": MAPPE["planung"] | {"laeufe": laeufe}})
        return [alarm for alarm in mit_plan(mappe).alarme if alarm.id == "a-brand"]

    def namen(self, alarm: Alarm) -> list[str]:
        return [fahrzeug.funkrufname for fahrzeug in alarm.einsatzmittel[0].fahrzeuge]

    def test_ueberschneidung_setzt_beide_auf_einen_zettel(self):
        """Die Zeit gehört dem Blatt, die Nummer dem Einsatz: wer später losfährt, steht später
        drauf und trägt trotzdem dieselbe Nummer."""
        zettel = self.zettel(("f-lhf", "08:00", "10:00"), ("f-mtf", "09:00", "11:00"))
        self.assertEqual(2, len(zettel))
        self.assertEqual([["LHF 6501.3", "MTF 6502.1"]] * 2, [self.namen(z) for z in zettel])
        self.assertEqual(["08:00", "09:00"], [z.einsatzZeit for z in zettel])
        self.assertEqual(zettel[0].einsatzNr, zettel[1].einsatzNr)

    def test_ohne_ueberschneidung_zwei_einsaetze(self):
        zettel = self.zettel(("f-lhf", "08:00", "09:00"), ("f-mtf", "10:00", "11:00"))
        self.assertEqual([["LHF 6501.3"], ["MTF 6502.1"]], [self.namen(z) for z in zettel])
        self.assertEqual(["08:00", "10:00"], [z.einsatzZeit for z in zettel])
        self.assertNotEqual(zettel[0].einsatzNr, zettel[1].einsatzNr)

    def test_luecke_von_null_minuten_trennt_auch(self):
        """Wer ankommt, wenn der andere weg ist, ist ein neuer Einsatz und kein Nachrücker."""
        zettel = self.zettel(("f-lhf", "08:00", "09:00"), ("f-mtf", "09:00", "10:00"))
        self.assertEqual([["LHF 6501.3"], ["MTF 6502.1"]], [self.namen(z) for z in zettel])

    def test_die_ueberschneidung_traegt_weiter(self):
        """A mit B und B mit C hält alle drei zusammen, auch wenn A und C sich nicht berühren."""
        zettel = self.zettel(("f-lhf", "08:00", "09:00"), ("f-mtf", "08:30", "10:00"),
                             ("f-rtw", "09:30", "11:00"))
        self.assertEqual(3, len(zettel))
        self.assertEqual({3}, {len(self.namen(z)) for z in zettel})


class EinsatznummerTest(unittest.TestCase):
    """
    Die Nummer kommt aus der Uhrzeit: der Anteil des Tages, der bis dahin vergangen ist, mal die
    Alarme, die die Leitstelle an einem Tag zählt.
    """

    def nummern(self, **kataloge) -> list[str]:
        mappe = Arbeitsmappe.model_validate(
            MAPPE | {"kataloge": MAPPE["kataloge"] | kataloge})
        return [alarm.einsatzNr for alarm in mit_plan(mappe).alarme if alarm.id != "a-frei"]

    def test_acht_uhr_dreissig_bei_2200_alarmen(self):
        """Beide Blätter desselben Alarms tragen dieselbe Nummer — die des ersten, der losfährt."""
        self.assertEqual(["779", "779"], self.nummern(alarmeProTag=2200))

    def test_ohne_angabe_bleibt_die_getippte_nummer(self):
        self.assertEqual(["", ""], self.nummern(alarmeProTag=0))


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

    def test_wer_nur_hinfaehrt_gehoert_nicht_zum_aufgebot(self):
        """Das MTF bringt die Mimen an die Lage und bleibt trotzdem unalarmiert."""
        laeufe = []
        for lauf in MAPPE["planung"]["laeufe"]:
            if lauf["fahrzeugId"] == "f-mtf":
                schritte = [schritt | {"aufgebot": False} for schritt in lauf["schritte"]]
                laeufe.append(lauf | {"schritte": schritte})
            else:
                laeufe.append(lauf)
        alarme = self.alarme(planung=MAPPE["planung"] | {"laeufe": laeufe})
        self.assertEqual(["a-brand", "a-frei"], [alarm.id for alarm in alarme])
        self.assertEqual(["LHF 6501.3"],
                         [fahrzeug.funkrufname
                          for fahrzeug in alarme[0].einsatzmittel[0].fahrzeuge])

    def test_ohne_fahrzeug_bleibt_das_getippte_aufgebot(self):
        """
        Sonst druckt der Zwischenstand „Lage da, Ketten noch nicht“ an niemanden adressiert. Auch
        die Adresse bleibt die getippte: die Lage findet dort statt, wo ihre Schritte stehen, und
        solange keiner steht, weiß der Plan den Ort nicht.
        """
        ohne = {**MAPPE["planung"], "laeufe": []}
        alarme = self.alarme(planung=ohne)
        self.assertEqual(["a-brand", "a-frei"], [alarm.id for alarm in alarme])
        self.assertEqual("1. Alarm", alarme[0].einsatzmittel[0].gruppe)
        self.assertEqual("07:00", alarme[0].einsatzZeit)
        self.assertEqual("Von Hand", alarme[0].einsatzadresse.strasse)

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
            {"id": "g-zweite", "name": "Noch eine", "alarmId": "a-brand"}]
        alarme = mit_plan(mappe(planung=MAPPE["planung"] | {"programmpunkte": punkte})).alarme
        self.assertEqual("Archenholdstraße", alarme[0].einsatzadresse.strasse)


class VorbereitungTest(unittest.TestCase):
    """
    Ein Fahrzeug steht oft schon vorher am Ort und richtet her. Die Vorbereitung ist ein eigener
    Schritt ohne Lage; alarmiert ist das Fahrzeug erst mit dem Schritt, der auf sie zeigt.
    """

    def alarm(self, laeufe: list[dict]):
        return mit_plan(mappe(planung=MAPPE["planung"] | {"laeufe": laeufe})).alarme[0]

    def test_die_vorbereitung_zaehlt_nicht_als_anfahrt(self):
        laeufe = [{"id": "l", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "fahrt",
             "von": "2026-09-19T07:00", "bis": "2026-09-19T07:30", "ortId": "o-kita"},
            {"id": "s2", "sortierung": 1.0, "art": "aufenthalt",
             "von": "2026-09-19T07:30", "bis": "2026-09-19T09:00", "ortId": "o-kita",
             "besatzung": [{"id": "b1", "personId": "p-alex", "faehrt": True}]},
            {"id": "s3", "sortierung": 2.0, "art": "aufenthalt", "programmpunktId": "g-brand",
             "von": "2026-09-19T09:00", "bis": "2026-09-19T10:00", "ortId": "o-kita",
             "besatzung": [{"id": "b2", "personId": "p-alex", "faehrt": True},
                           {"id": "b3", "personId": "p-mimen"}]}]}]
        alarm = self.alarm(laeufe)
        self.assertEqual("09:00", alarm.einsatzZeit)
        self.assertEqual("5", alarm.einsatzmittel[0].fahrzeuge[0].staerke)

    def test_wer_zur_lage_faehrt_wird_ab_der_abfahrt_gezaehlt(self):
        """Fährt das Fahrzeug dagegen für die Lage los, ist deren Beginn die Einsatzzeit."""
        laeufe = [{"id": "l", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "aufenthalt",
             "von": "2026-09-19T08:00", "bis": "2026-09-19T08:30", "ortId": "o-nord"},
            {"id": "s2", "sortierung": 1.0, "art": "fahrt",
             "von": "2026-09-19T08:30", "bis": "2026-09-19T09:00", "ortId": "o-kita"},
            {"id": "s3", "sortierung": 2.0, "art": "aufenthalt", "programmpunktId": "g-brand",
             "von": "2026-09-19T09:00", "bis": "2026-09-19T10:00", "ortId": "o-kita"}]}]
        self.assertEqual("08:30", self.alarm(laeufe).einsatzZeit)


class ZweiLagenTest(unittest.TestCase):
    """Am selben Ort laufen zwei Lagen nacheinander — jede hat ihren eigenen Zettel."""

    def alarme(self):
        punkte = [
            {"id": "g-brand", "name": "Brand", "ortId": "o-kita", "alarmId": "a-brand"},
            {"id": "g-rea", "name": "Rea", "ortId": "o-kita", "alarmId": "a-frei"},
        ]
        laeufe = [{"id": "l", "fahrzeugId": "f-lhf", "schritte": [
            {"id": "s1", "sortierung": 0.0, "art": "fahrt",
             "von": "2026-09-19T08:30", "bis": "2026-09-19T09:00", "ortId": "o-kita"},
            {"id": "s2", "sortierung": 1.0, "art": "aufenthalt", "programmpunktId": "g-brand",
             "von": "2026-09-19T09:00", "bis": "2026-09-19T10:00", "ortId": "o-kita",
             "besatzung": [{"id": "b1", "personId": "p-alex", "faehrt": True}]},
            {"id": "s3", "sortierung": 2.0, "art": "aufenthalt", "programmpunktId": "g-rea",
             "von": "2026-09-19T10:00", "bis": "2026-09-19T11:00", "ortId": "o-kita",
             "besatzung": [{"id": "b2", "personId": "p-alex", "faehrt": True},
                           {"id": "b3", "personId": "p-mimen"}]}]}]
        return mit_plan(mappe(planung=MAPPE["planung"] | {
            "programmpunkte": punkte, "laeufe": laeufe})).alarme

    def test_jede_lage_bekommt_ihre_eigene_zeit(self):
        zeiten = {alarm.id: alarm.einsatzZeit for alarm in self.alarme()}
        self.assertEqual({"a-brand": "08:30", "a-frei": "10:00"}, zeiten)

    def test_und_ihre_eigene_staerke(self):
        staerken = {alarm.id: alarm.einsatzmittel[0].fahrzeuge[0].staerke
                    for alarm in self.alarme()}
        self.assertEqual({"a-brand": "1", "a-frei": "5"}, staerken)


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
        self.assertEqual("Brand M", gefunden["lage"])
        self.assertEqual("Archenholdstraße", gefunden["einsatzadresse"]["strasse"])
        self.assertEqual(
            [("LHF 6501.3", "5", "08:30"), ("MTF 6502.1", "1", "09:00")],
            [(blatt["funkrufname"], blatt["staerke"], blatt["einsatzZeit"])
             for blatt in gefunden["blaetter"]])


if __name__ == "__main__":
    unittest.main()
