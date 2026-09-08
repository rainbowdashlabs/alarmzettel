"""
The Berlin address list: downloaded once, then queried locally.

The source is the city's address WFS — some 400 000 points carrying street, house number,
postcode, Ortsteil and the official coordinates in ETRS89 / UTM 33N. It is not committed and not
part of the image: the server fetches it into a cache the first time it gets the chance, and
again once the copy grows old. Nothing about startup depends on it. Until a download has
finished, completion has nothing to offer and the address fields stay what they always were,
plain text.

Lookups run here rather than in the browser because the whole list has no business travelling to
a client that needs a dozen rows of it.
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator

import httpx

DIENST = "https://gdi.berlin.de/services/wfs/adressen_berlin"
TYPNAME = "adressen_berlin:adressen_berlin"
FELDER = "str_name,hnr,hnr_zusatz,plz,ort_name,geom"
SEITE = 20000

SCHEMA = """
CREATE TABLE adressen (
    strasse   TEXT NOT NULL,
    suche     TEXT NOT NULL,
    hnr       INTEGER NOT NULL,
    zusatz    TEXT NOT NULL,
    plz       TEXT NOT NULL,
    ort       TEXT NOT NULL,
    ostwert   REAL NOT NULL,
    nordwert  REAL NOT NULL
);
CREATE TABLE stand (geholt TEXT NOT NULL);
"""

INDIZES = """
CREATE INDEX adressen_suche ON adressen (suche, hnr);
"""


class Adressen:
    """
    The downloaded address list and the queries the editor puts to it.

    Every method has to cope with the file not being there, because for the first minute of a
    fresh installation it is not, and on a machine with no route to the outside it never will be.
    """

    def __init__(self, datei: Path, hoechstalter_tage: int = 30):
        self.datei = datei
        self.hoechstalter = timedelta(days=hoechstalter_tage)

    @contextmanager
    def _lesen(self) -> Iterator[sqlite3.Connection | None]:
        """Opens the cache read-only, or yields nothing at all when there is no cache yet."""
        if not self.datei.is_file():
            yield None
            return
        verbindung = sqlite3.connect(f"file:{self.datei}?mode=ro", uri=True)
        verbindung.row_factory = sqlite3.Row
        try:
            yield verbindung
        finally:
            verbindung.close()

    def bestand(self) -> dict:
        with self._lesen() as verbindung:
            if verbindung is None:
                return {"verfuegbar": False, "anzahl": 0, "stand": None}
            anzahl = verbindung.execute("SELECT count(*) FROM adressen").fetchone()[0]
            zeile = verbindung.execute("SELECT geholt FROM stand").fetchone()
            return {"verfuegbar": anzahl > 0, "anzahl": anzahl,
                    "stand": zeile["geholt"] if zeile else None}

    def veraltet(self) -> bool:
        """True when there is no copy, or the one there is has passed its refresh age."""
        bestand = self.bestand()
        if not bestand["verfuegbar"] or not bestand["stand"]:
            return True
        geholt = datetime.fromisoformat(bestand["stand"])
        return datetime.now(UTC) - geholt > self.hoechstalter

    ANGEHAENGT = re.compile(r"^(?P<strasse>.*?)[\s,]+(?P<hnr>\d+\s*[a-zA-Z]?)$")

    @classmethod
    def _zerlegen(cls, text: str) -> tuple[str, str]:
        """
        Splits "Archenholdstr 21" into the street and the house number, so one field can carry a
        whole address. A trailing word that is not a number stays part of the name — "Straße des
        17. Juni" is a street, not a street and a number.
        """
        treffer = cls.ANGEHAENGT.match(text.strip())
        if not treffer:
            return text.strip(), ""
        return treffer.group("strasse").strip(), treffer.group("hnr")

    def suchen(self, text: str, grenze: int = 12) -> list[dict]:
        """
        What to offer for what has been typed so far.

        Without a house number these are streets, each listed once per postcode and Ortsteil it
        runs through, because a long street crosses several and the sheet wants the right one.
        With one they are doors, carrying the coordinates, so picking a suggestion settles the
        whole address at once.
        """
        name, hnr = self._zerlegen(text)
        anfang = name.lower()
        if len(anfang) < 2:
            return []
        with self._lesen() as verbindung:
            if verbindung is None:
                return []
            if not hnr:
                zeilen = verbindung.execute(
                    "SELECT strasse, plz, ort, count(*) AS anzahl FROM adressen "
                    "WHERE suche LIKE ? || '%' GROUP BY strasse, plz, ort "
                    "ORDER BY strasse, plz LIMIT ?", (anfang, grenze)).fetchall()
                return [{"beschriftung": f"{zeile['strasse']}, {zeile['plz']} {zeile['ort']}",
                         "strasse": zeile["strasse"], "hnr": "",
                         "plz": zeile["plz"], "ort": zeile["ort"],
                         "ostwert": None, "nordwert": None} for zeile in zeilen]

            zahl, zusatz = self._hausnummer(hnr)
            bedingung = "suche LIKE ? || '%' AND hnr = ?"
            werte: list = [anfang, zahl]
            if zusatz:
                bedingung += " AND zusatz = ?"
                werte.append(zusatz)
            werte.append(grenze)
            zeilen = verbindung.execute(
                f"SELECT strasse, hnr, zusatz, plz, ort, ostwert, nordwert FROM adressen "
                f"WHERE {bedingung} ORDER BY strasse, zusatz, plz LIMIT ?", werte).fetchall()
            return [self._beschriftet(zeile) for zeile in zeilen]

    @classmethod
    def _beschriftet(cls, zeile: sqlite3.Row) -> dict:
        eintrag = cls._eintrag(zeile)
        return {"beschriftung": f"{eintrag['strasse']} {eintrag['hnr']}, "
                                f"{eintrag['plz']} {eintrag['ort']}", **eintrag}

    def finden(self, strasse: str, hnr: str, plz: str = "") -> dict | None:
        """
        One address, as exactly as the three given parts allow. A house number carrying a letter
        is matched on both halves; "28" and "28 A" are different doors.
        """
        zahl, zusatz = self._hausnummer(hnr)
        if zahl is None:
            return None
        bedingung = "suche = ? AND hnr = ? AND zusatz = ?"
        werte: list = [strasse.strip().lower(), zahl, zusatz]
        if plz.strip():
            bedingung += " AND plz = ?"
            werte.append(plz.strip())
        with self._lesen() as verbindung:
            if verbindung is None:
                return None
            zeile = verbindung.execute(
                f"SELECT strasse, hnr, zusatz, plz, ort, ostwert, nordwert FROM adressen "
                f"WHERE {bedingung} LIMIT 1", werte).fetchone()
            return self._eintrag(zeile) if zeile else None

    @staticmethod
    def _hausnummer(roh: str) -> tuple[int | None, str]:
        """Splits "28A" or "28 a" into the number and its upper-case suffix."""
        ziffern = ""
        for zeichen in roh.strip():
            if not zeichen.isdigit():
                break
            ziffern += zeichen
        if not ziffern:
            return None, ""
        return int(ziffern), roh.strip()[len(ziffern):].strip().upper()

    @staticmethod
    def _eintrag(zeile: sqlite3.Row) -> dict:
        return {"strasse": zeile["strasse"], "hnr": f"{zeile['hnr']}{zeile['zusatz']}",
                "plz": zeile["plz"], "ort": zeile["ort"],
                "ostwert": zeile["ostwert"], "nordwert": zeile["nordwert"]}

    def laden(self) -> int:
        """
        Fetches the whole list and replaces the cache with it.

        Written to a file beside the target and renamed into place, so a download that dies
        halfway leaves the copy that was already there intact and queryable.
        """
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        neu = self.datei.with_name(self.datei.name + ".neu")
        neu.unlink(missing_ok=True)

        verbindung = sqlite3.connect(neu)
        try:
            verbindung.executescript(SCHEMA)
            anzahl = 0
            with httpx.Client(timeout=180.0, follow_redirects=True) as klient:
                start = 0
                while True:
                    merkmale = self._seite(klient, start)
                    if not merkmale:
                        break
                    verbindung.executemany(
                        "INSERT INTO adressen VALUES (?, ?, ?, ?, ?, ?, ?, ?)", merkmale)
                    anzahl += len(merkmale)
                    start += SEITE
            verbindung.executescript(INDIZES)
            verbindung.execute("INSERT INTO stand VALUES (?)", (datetime.now(UTC).isoformat(),))
            verbindung.commit()
        finally:
            verbindung.close()

        os.replace(neu, self.datei)
        return anzahl

    @staticmethod
    def _seite(klient: httpx.Client, start: int) -> list[tuple]:
        antwort = klient.get(DIENST, params={
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": TYPNAME, "OUTPUTFORMAT": "application/json",
            "PROPERTYNAME": FELDER, "COUNT": SEITE, "STARTINDEX": start,
        })
        antwort.raise_for_status()
        zeilen = []
        for merkmal in antwort.json().get("features", []):
            eigenschaft = merkmal.get("properties") or {}
            geometrie = (merkmal.get("geometry") or {}).get("coordinates")
            strasse = eigenschaft.get("str_name")
            hnr = eigenschaft.get("hnr")
            if not strasse or hnr is None or not geometrie:
                continue
            zeilen.append((
                strasse, strasse.lower(), int(hnr),
                (eigenschaft.get("hnr_zusatz") or "").strip().upper(),
                eigenschaft.get("plz") or "", eigenschaft.get("ort_name") or "",
                float(geometrie[0]), float(geometrie[1]),
            ))
        return zeilen
