"""
Der Ablaufplan eines Übungstages.

Geplant wird als Kette: ein Fahrzeug oder eine Person hat eine Folge von Schritten, und jeder
fängt an, wo der vorige aufgehört hat. Der Startort einer Fahrt wird deshalb nirgends gespeichert
— er steht schon fest, und ein Sprung von A nach B ohne Weg dazwischen ist nicht darstellbar
statt nur falsch.

Der Personenplan wird aus denselben Daten gerechnet und nirgends gepflegt: alle Schritte, in
deren Besatzung jemand steht, plus die eigenen.
"""

from typing import Literal

from entities.basis import Adresse, Eintrag

ROLLEN = ["Ausbilder", "Teilnehmer", "Mime", "Foto", "Beobachter"]
FAHRERLAUBNISSE = ["B", "BE", "C1", "C1E", "C", "CE"]


class Tag(Eintrag):
    """Ein Tag der Veranstaltung. Eigene Liste, damit auch ein leerer Tag angelegt sein kann."""

    datum: str = ""
    name: str = ""


class Ort(Eintrag):
    """
    Ein eingetragener Ort mit einer Identität — kein Text in einer Zelle. Nur dadurch ist „am
    selben Ort zur selben Zeit“ entscheidbar, woran Fahrerwechsel, Zustieg und Übergabe hängen.
    """

    name: str = ""
    adresse: Adresse = Adresse()


class Verfuegbarkeit(Eintrag):
    """Ein Fenster, in dem jemand da ist. Keines eingetragen heißt: immer."""

    von: str = ""
    bis: str = ""


class Person(Eintrag):
    name: str = ""
    rollen: list[str] = []
    """Führerscheinklassen, gegen `Fahrzeugvorlage.fuehrerschein` geprüft."""
    fahrerlaubnis: list[str] = []
    """Wie viele Köpfe diese Zeile bedeutet — „Mimen (4)“ belegt vier Plätze."""
    anzahl: int = 1
    verfuegbar: list[Verfuegbarkeit] = []


class Programmpunkt(Eintrag):
    """
    Die Lage als solche, ohne Zeiten und ohne Teilnehmer: wann sie läuft und wer dabei ist, sagen
    die Schritte, die auf sie zeigen. So kann sie sich nicht selbst widersprechen.
    """

    name: str = ""
    ortId: str = ""
    alarmId: str = ""


class Besatzung(Eintrag):
    personId: str = ""
    faehrt: bool = False


class Schritt(Eintrag):
    """
    Entweder an einem Ort sein oder zu einem fahren. Die Besatzung ist die vollständige Liste für
    diesen Schritt, nicht die Änderung gegenüber dem vorigen — dadurch ist jeder Schritt für sich
    lesbar und jede Prüfung eine Frage an einen einzelnen Schritt.
    """

    art: Literal["aufenthalt", "fahrt"] = "aufenthalt"
    mittel: Literal["fahrzeug", "fuss", "eigen"] = "fahrzeug"
    von: str = ""
    bis: str = ""
    """Wo man ist, beziehungsweise wohin es geht. Woher, sagt der vorige Schritt."""
    ortId: str = ""
    programmpunktId: str = ""
    besatzung: list[Besatzung] = []


class Lauf(Eintrag):
    """Die Kette eines Fahrzeugs oder einer Person. Genau eines von beiden ist gesetzt."""

    fahrzeugId: str = ""
    personId: str = ""
    schritte: list[Schritt] = []


class Planung(Eintrag):
    """Aus: kein Navigationspunkt, keine Daten, der Alarmzettel-Teil unverändert."""

    aktiv: bool = False
    tage: list[Tag] = []
    orte: list[Ort] = []
    personen: list[Person] = []
    rollen: list[str] = []
    fahrerlaubnisse: list[str] = []
    programmpunkte: list[Programmpunkt] = []
    laeufe: list[Lauf] = []
