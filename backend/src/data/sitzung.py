"""
Sitzungen: jede Arbeitsmappe liegt hier, und ein Link darauf ist das Teilen.

Eine Sitzung ist eine JSON-Datei im Volume plus eine Zeile in einem SQLite-Index. Das Token ist
das Einzige, was zur Datei führt, deshalb ist es lang und zufällig; wer es hat, darf lesen und
schreiben. Eine Anmeldung gibt es nicht.

Die Datei hält das Dokument als Merge-Fakten, nicht als fertige Arbeitsmappe, damit zwei
gleichzeitige Schreiber beide Änderungen behalten — siehe data/dokument.py. Schreibvorgänge sind
je Sitzung durch das Schloss serialisiert, was die Revisionsnummern zu einer totalen Ordnung
macht.

Eine Sitzung läuft 30 Tage nach der letzten Benutzung ab, nicht nach dem Anlegen — was in
Gebrauch ist, bleibt; was niemand öffnet, geht. Der Aufräumer löscht Zeile und Datei zusammen.

**Der Speicher ist ein Cache, keine Ablage.** Die Platte ist die Wahrheit; geöffnete Sitzungen
liegen zusätzlich im Speicher, weil sonst jede Abgleichsabfrage — alle drei Sekunden je Browser —
die Datei liest und parst. Wer eine Weile nicht angefasst wurde, fliegt raus und wird beim
nächsten Zugriff wieder von der Platte gelesen. Verdrängung kann deshalb nie Daten kosten.

Die Namen auf der Platte hießen einmal „Freigabe“. Der Verzeichnis- und der Dateiname bleiben,
wie sie sind, weil ein Umbenennen bestehende Sitzungen von ihren Dateien trennen würde; die
Tabelle wird beim Start einmalig umbenannt.
"""

import contextlib
import json
import secrets
import sqlite3
import threading
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data.dokument import Dokument

SCHEMA = """
CREATE TABLE IF NOT EXISTS sitzungen (
    token       TEXT PRIMARY KEY,
    angelegt    TEXT NOT NULL,
    zuletzt     TEXT NOT NULL,
    alarme      INTEGER NOT NULL DEFAULT 0,
    bytes       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sitzungen_zuletzt ON sitzungen (zuletzt);
"""


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


class SitzungFehler(RuntimeError):
    """Die Sitzung ist nicht auslieferbar: Token unbekannt, oder die Datei ist weg."""


class Sitzungen:
    def __init__(self, verzeichnis: Path, tage: int,
                 cache_eintraege: int = 64, cache_minuten: int = 30):
        self._verzeichnis = verzeichnis
        self._tage = tage
        self._cache_eintraege = cache_eintraege
        self._cache_sekunden = cache_minuten * 60
        self._lock = threading.Lock()
        # One lock per session, so a busy workspace does not hold up the others. The outer lock
        # only guards handing these out.
        self._sperren: dict[str, threading.Lock] = defaultdict(threading.Lock)
        # Zuletzt benutzt zuletzt: das Verdrängen nimmt vom Anfang.
        self._cache: OrderedDict[str, tuple[Dokument, float]] = OrderedDict()
        self._cache_lock = threading.Lock()
        self._umbenennen()

    def _umbenennen(self) -> None:
        """
        Die Tabelle hieß einmal `freigaben`. Einmalig umbenennen, damit bestehende Sitzungen den
        Namenswechsel überleben.

        Läuft mit einer eigenen Verbindung, bevor irgendetwas das Schema anlegt: `_verbindung`
        legt die neue Tabelle bei jedem Öffnen an, und gegen eine bereits vorhandene leere
        Tabelle würde das Umbenennen scheitern und die alten Zeilen liegen lassen.
        """
        self._verzeichnis.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self._verzeichnis / "freigaben.sqlite", timeout=10)
        try:
            namen = {zeile[0] for zeile in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
            if "freigaben" in namen and "sitzungen" not in namen:
                db.execute("ALTER TABLE freigaben RENAME TO sitzungen")
                db.commit()
        finally:
            db.close()

    @contextlib.contextmanager
    def _verbindung(self):
        """
        `with sqlite3.connect(...)` commits but never closes, which in a server that runs for
        weeks is a handle leak. This commits and closes.
        """
        self._verzeichnis.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self._verzeichnis / "freigaben.sqlite", timeout=10)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            # Bei jeder Verbindung, nicht nur beim Start: ein Volume, das unter dem laufenden
            # Server geleert oder neu eingehängt wird, soll den Dienst nicht mitnehmen. Beide
            # Anweisungen sind IF NOT EXISTS und kosten neben dem Dateilesen nichts.
            db.executescript(SCHEMA)
            yield db
            db.commit()
        finally:
            db.close()

    def _datei(self, token: str) -> Path:
        return self._verzeichnis / f"{token}.json"

    def _sperre(self, token: str) -> threading.Lock:
        with self._lock:
            return self._sperren[token]

    def _aus_cache(self, token: str) -> Dokument | None:
        with self._cache_lock:
            eintrag = self._cache.get(token)
            if eintrag is None:
                return None
            self._cache[token] = (eintrag[0], time.monotonic())
            self._cache.move_to_end(token)
            return eintrag[0]

    def _in_cache(self, token: str, dokument: Dokument) -> None:
        with self._cache_lock:
            self._cache[token] = (dokument, time.monotonic())
            self._cache.move_to_end(token)
            self._verdraengen()

    def _verdraengen(self) -> None:
        """
        Nach Zeit und nach Zahl. Ein Server mit vielen Sitzungen soll nicht alle im Speicher
        halten müssen, nur weil sie alle jung sind. Aufrufer hält `_cache_lock`.
        """
        grenze = time.monotonic() - self._cache_sekunden
        for token in [t for t, (_, wann) in self._cache.items() if wann < grenze]:
            del self._cache[token]
        while len(self._cache) > self._cache_eintraege:
            self._cache.popitem(last=False)

    def _vergessen(self, token: str) -> None:
        with self._cache_lock:
            self._cache.pop(token, None)

    def _laden(self, token: str) -> Dokument:
        """Aus dem Cache, sonst von der Platte. Der Aufrufer hält das Schloss der Sitzung."""
        gecacht = self._aus_cache(token)
        if gecacht is not None:
            return gecacht
        with self._verbindung() as db:
            if db.execute("SELECT 1 FROM sitzungen WHERE token = ?", (token,)).fetchone() is None:
                raise SitzungFehler("Diese Sitzung gibt es nicht mehr.")
        datei = self._datei(token)
        if not datei.is_file():
            with self._verbindung() as db:
                db.execute("DELETE FROM sitzungen WHERE token = ?", (token,))
            raise SitzungFehler("Diese Sitzung gibt es nicht mehr.")
        dokument = Dokument.laden(json.loads(datei.read_text(encoding="utf-8")))
        self._in_cache(token, dokument)
        return dokument

    def _schreiben(self, token: str, dokument: Dokument, alarme: int) -> None:
        roh = json.dumps(dokument.sichern(), ensure_ascii=False).encode("utf-8")
        # Written beside the target and moved into place, so a crash mid-write cannot leave a
        # half-written document where a readable one used to be.
        vorlaeufig = self._datei(token).with_suffix(".json.neu")
        vorlaeufig.write_bytes(roh)
        vorlaeufig.replace(self._datei(token))
        self._in_cache(token, dokument)
        with self._verbindung() as db:
            db.execute("UPDATE sitzungen SET zuletzt = ?, alarme = ?, bytes = ? WHERE token = ?",
                       (_jetzt().isoformat(), alarme, len(roh), token))

    def anlegen(self, arbeitsmappe: dict) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        dokument = Dokument.aus_arbeitsmappe(arbeitsmappe)
        jetzt = _jetzt()
        with self._sperre(token):
            with self._verbindung() as db:
                db.execute(
                    "INSERT INTO sitzungen (token, angelegt, zuletzt, alarme, bytes)"
                    " VALUES (?, ?, ?, 0, 0)",
                    (token, jetzt.isoformat(), jetzt.isoformat()))
            self._schreiben(token, dokument, len(arbeitsmappe.get("alarme", [])))
        return token, jetzt + timedelta(days=self._tage)

    def lesen(self, token: str) -> tuple[dict, datetime]:
        """Reading pushes the expiry out, so a link in use does not go away underneath anyone."""
        with self._sperre(token):
            dokument = self._laden(token)
            with self._verbindung() as db:
                db.execute("UPDATE sitzungen SET zuletzt = ? WHERE token = ?",
                           (_jetzt().isoformat(), token))
            return dokument.arbeitsmappe(), _jetzt() + timedelta(days=self._tage)

    def stand(self, token: str, seit: int) -> dict:
        """What changed since the caller last heard, and where the document stands now."""
        with self._sperre(token):
            dokument = self._laden(token)
            with self._verbindung() as db:
                db.execute("UPDATE sitzungen SET zuletzt = ? WHERE token = ?",
                           (_jetzt().isoformat(), token))
            return {"stand": dokument.stand, "aenderungen": dokument.seit(seit)}

    def schreiben(self, token: str, aenderungen: list[dict], wer: str, seit: int) -> dict:
        """
        Applies one client's batch and answers with everything it has not seen — including what
        just arrived from someone else. Held under the share's lock, so two writers landing at
        the same moment are ordered rather than interleaved.
        """
        with self._sperre(token):
            dokument = self._laden(token)
            dokument.anwenden(aenderungen, wer)
            arbeitsmappe = dokument.arbeitsmappe()
            self._schreiben(token, dokument, len(arbeitsmappe.get("alarme", [])))
            return {"stand": dokument.stand, "aenderungen": dokument.seit(seit)}

    def loeschen(self, token: str) -> bool:
        self._vergessen(token)
        with self._lock:
            self._datei(token).unlink(missing_ok=True)
            with self._verbindung() as db:
                return db.execute("DELETE FROM sitzungen WHERE token = ?",
                                  (token,)).rowcount > 0

    def aufraeumen(self) -> int:
        """Drops everything unread for longer than the retention, file and row together."""
        grenze = (_jetzt() - timedelta(days=self._tage)).isoformat()
        with self._lock:
            fort: list[str] = []
            with self._verbindung() as db:
                abgelaufen = [z[0] for z in db.execute(
                    "SELECT token FROM sitzungen WHERE zuletzt < ?", (grenze,)).fetchall()]
                for token in abgelaufen:
                    fort.append(token)
                    self._datei(token).unlink(missing_ok=True)
                    db.execute("DELETE FROM sitzungen WHERE token = ?", (token,))

            # A file without a row is orphaned - a crash between the write and the insert, or a
            # volume restored from elsewhere. Nothing can reach it, so it goes too.
            with self._verbindung() as db:
                bekannt = {z[0] for z in db.execute("SELECT token FROM sitzungen").fetchall()}
            for datei in self._verzeichnis.glob("*.json.neu"):
                datei.unlink(missing_ok=True)
            for datei in self._verzeichnis.glob("*.json"):
                if datei.stem not in bekannt:
                    datei.unlink(missing_ok=True)
                    abgelaufen.append(datei.stem)
        for token in fort:
            self._vergessen(token)
        return len(abgelaufen)

    def im_speicher(self) -> int:
        """Wie viele Sitzungen gerade im Cache liegen — für die Gesundheitsanzeige."""
        with self._cache_lock:
            return len(self._cache)

    def anzahl(self) -> int:
        with self._verbindung() as db:
            return db.execute("SELECT COUNT(*) FROM sitzungen").fetchone()[0]
