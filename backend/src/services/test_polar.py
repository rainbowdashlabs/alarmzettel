import unittest

from data.katalog import mit_katalog
from data.polar import polar_koordinaten
from entities.alarm import Adresse, Alarm, Arbeitsmappe, Karte, Kataloge
from services.render import _mit_polar

WACHE = {"ostwert": 399598.791, "nordwert": 5815944.114}
"""Feuerwache Karlshorst, Junker-Jörg-Straße 36, aus dem Berliner Adressregister."""


class PolarTest(unittest.TestCase):
    """
    Dieselben Fälle, die `tools/polar_pruefen` im Browser prüft — die beiden Rechnungen müssen
    dasselbe ergeben, sonst hinge es davon ab, wer den Zettel erzeugt hat.
    """

    def test_gegen_einen_echten_zettel(self):
        """
        Der Zettel druckt 336,6°/2,849 km. Der Winkel stimmt auf die Stelle; die sieben Meter
        sind der Unterschied zwischen dem Punkt des Registers und dem, von dem die Leitstelle
        misst.
        """
        ziel = {"ostwert": 398470.239, "nordwert": 5818552.633}
        self.assertEqual("336,6°/2,842 km", polar_koordinaten(WACHE, ziel))

    def test_unter_einem_kilometer_fuehrt_die_null_als_leerzeichen(self):
        ziel = {"ostwert": WACHE["ostwert"] + 60.7, "nordwert": WACHE["nordwert"] + 340.6}
        self.assertEqual("10,1°/ ,346 km", polar_koordinaten(WACHE, ziel))


class ImAusdruckTest(unittest.TestCase):
    """
    Gerechnet wird beim Drucken und nicht nur, während jemand eine Adresse im Editor auflöst —
    sonst trüge im Stapel allein der Zettel Polar-Koordinaten, den zuletzt jemand offen hatte.
    """

    def mappe(self, **karte) -> Arbeitsmappe:
        return Arbeitsmappe(
            alarme=[Alarm(id="a1", karte=Karte(**karte),
                          einsatzadresse=Adresse(strasse="Archenholdstraße", hnr="21",
                                                 koordinaten="52.50763155, 13.50404047"))],
            kataloge=Kataloge(wache=Adresse(strasse="Junker-Jörg-Straße", hnr="36",
                                            koordinaten="52.48439726, 13.52144944")))

    def gedruckt(self, mappe: Arbeitsmappe) -> str:
        return _mit_polar(mit_katalog(mappe)).alarme[0].karte.polarKoordinaten

    def test_leer_wird_gerechnet(self):
        self.assertEqual("336,6°/2,842 km", self.gedruckt(self.mappe()))

    def test_eingetragenes_bleibt_stehen(self):
        self.assertEqual("von Hand", self.gedruckt(self.mappe(polarKoordinaten="von Hand")))

    def test_ohne_ziel_bleibt_es_leer(self):
        mappe = self.mappe()
        mappe.alarme[0].einsatzadresse = Adresse()
        self.assertEqual("", self.gedruckt(mappe))
