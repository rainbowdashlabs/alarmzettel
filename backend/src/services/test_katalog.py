import unittest

from data.katalog import mit_katalog
from entities.alarm import (Adresse, Alarm, Arbeitsmappe, Einsatzmittelgruppe, Fahrzeug,
                            Fahrzeugvorlage, Kataloge)

VORLAGE = Fahrzeugvorlage(funkrufname="LHF 6501.3", staerke="6", ezp="6", status="R2(A1)")


def mappe(*fahrzeuge: Fahrzeug, katalog=(VORLAGE,)) -> Arbeitsmappe:
    return Arbeitsmappe(
        alarme=[Alarm(id="a1", einsatzmittel=[Einsatzmittelgruppe(fahrzeuge=list(fahrzeuge))])],
        kataloge=Kataloge(fahrzeuge=[vorlage.model_copy(deep=True) for vorlage in katalog]),
    )


def erstes(arbeitsmappe: Arbeitsmappe) -> Fahrzeug:
    return mit_katalog(arbeitsmappe).alarme[0].einsatzmittel[0].fahrzeuge[0]


class KatalogTest(unittest.TestCase):
    def test_an_empty_field_comes_from_the_catalogue(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="LHF 6501.3")))
        self.assertEqual(("6", "R2(A1)", "6"), (fahrzeug.ezp, fahrzeug.status, fahrzeug.staerke))

    def test_the_trupp_follows_the_strength_the_catalogue_gave(self):
        self.assertEqual("Stärke=6: SF, AT, WT", erstes(mappe(Fahrzeug(funkrufname="LHF 6501.3"))).trupp)

    def test_a_value_on_the_alarm_overrides_that_field_alone(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="LHF 6501.3", status="R1")))
        self.assertEqual("R1", fahrzeug.status)
        self.assertEqual("6", fahrzeug.ezp)

    def test_an_overridden_strength_carries_its_own_trupps(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="LHF 6501.3", staerke="9")))
        self.assertEqual("Stärke=9: SF, AT, WT, ST, ME", fahrzeug.trupp)

    def test_a_written_trupp_line_is_left_alone(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="LHF 6501.3", trupp="Stärke=6: 51F, 52F")))
        self.assertEqual("Stärke=6: 51F, 52F", fahrzeug.trupp)

    def test_the_funkrufname_matches_regardless_of_case_and_padding(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="  lhf 6501.3 ")))
        self.assertEqual("6", fahrzeug.ezp)

    def test_a_vehicle_the_catalogue_does_not_know_keeps_what_it_was_given(self):
        fahrzeug = erstes(mappe(Fahrzeug(funkrufname="RTW 9999.1", ezp="2", staerke="2")))
        self.assertEqual(("2", "", "2"), (fahrzeug.ezp, fahrzeug.status, fahrzeug.staerke))
        self.assertEqual("Stärke=2: SF", fahrzeug.trupp)

    def test_a_correction_in_the_catalogue_reaches_the_sheet(self):
        arbeitsmappe = mappe(Fahrzeug(funkrufname="LHF 6501.3"))
        self.assertEqual("R2(A1)", erstes(arbeitsmappe).status)
        arbeitsmappe.kataloge.fahrzeuge[0].status = "R1"
        self.assertEqual("R1", erstes(arbeitsmappe).status)

    def test_resolving_does_not_write_back_into_the_working_set(self):
        arbeitsmappe = mappe(Fahrzeug(funkrufname="LHF 6501.3"))
        mit_katalog(arbeitsmappe)
        self.assertEqual("", arbeitsmappe.alarme[0].einsatzmittel[0].fahrzeuge[0].ezp)


class AnfahrtsadresseTest(unittest.TestCase):
    """
    Wohin gefahren wird, ist die Einsatzadresse — außer jemand hat ausdrücklich eine andere
    eingetragen.
    """

    def anfahrt(self, alarm: Alarm) -> Adresse:
        arbeitsmappe = Arbeitsmappe(alarme=[alarm], kataloge=Kataloge())
        return mit_katalog(arbeitsmappe).alarme[0].anfahrtsadresse

    def test_leer_heisst_wie_die_einsatzadresse(self):
        alarm = Alarm(id="a1", einsatzadresse=Adresse(strasse="Archenholdstraße", hnr="21"))
        self.assertEqual(("Archenholdstraße", "21"),
                         (self.anfahrt(alarm).strasse, self.anfahrt(alarm).hnr))

    def test_eine_eingetragene_bleibt_stehen(self):
        alarm = Alarm(id="a1", einsatzadresse=Adresse(strasse="Archenholdstraße", hnr="21"),
                      anfahrtsadresse=Adresse(strasse="Hintereingang"))
        self.assertEqual("Hintereingang", self.anfahrt(alarm).strasse)

    def test_die_arbeitsmappe_bleibt_unberuehrt(self):
        alarm = Alarm(id="a1", einsatzadresse=Adresse(strasse="Archenholdstraße"))
        arbeitsmappe = Arbeitsmappe(alarme=[alarm], kataloge=Kataloge())
        mit_katalog(arbeitsmappe)
        self.assertEqual("", arbeitsmappe.alarme[0].anfahrtsadresse.strasse)
