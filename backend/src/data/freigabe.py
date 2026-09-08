"""
Shared working sets: a link several people can work in at once.

A share is a JSON file in a volume plus a row in a SQLite index. The token in the link is the
only thing that reaches the file, so it is generated long and random; anyone holding the link can
read and write the share, which is what a share link is for.

The file holds the document as merge facts rather than as a finished working set, so two people
writing at once keep both changes — see data/dokument.py. Writes are serialised per share by the
lock, which is what makes the revision numbers a total order.

A share expires 30 days after it was last touched, not after it was created — a link that stays
in use stays alive, and one nobody opens goes away. The reaper runs on a schedule and deletes the
row and the file together.
"""

import contextlib
import json
import secrets
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data.dokument import Dokument

SCHEMA = """
CREATE TABLE IF NOT EXISTS freigaben (
    token       TEXT PRIMARY KEY,
    angelegt    TEXT NOT NULL,
    zuletzt     TEXT NOT NULL,
    alarme      INTEGER NOT NULL DEFAULT 0,
    bytes       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS freigaben_zuletzt ON freigaben (zuletzt);
"""


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


class FreigabeFehler(RuntimeError):
    """The share cannot be served: unknown token, or the file is gone."""


class Freigaben:
    def __init__(self, verzeichnis: Path, tage: int):
        self._verzeichnis = verzeichnis
        self._tage = tage
        self._lock = threading.Lock()
        # One lock per share, so a busy workspace does not hold up the others. The outer lock
        # only guards handing these out.
        self._sperren: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._verzeichnis.mkdir(parents=True, exist_ok=True)
        with self._verbindung() as db:
            db.executescript(SCHEMA)

    @contextlib.contextmanager
    def _verbindung(self):
        """
        `with sqlite3.connect(...)` commits but never closes, which in a server that runs for
        weeks is a handle leak. This commits and closes.
        """
        db = sqlite3.connect(self._verzeichnis / "freigaben.sqlite", timeout=10)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            db.commit()
        finally:
            db.close()

    def _datei(self, token: str) -> Path:
        return self._verzeichnis / f"{token}.json"

    def _sperre(self, token: str) -> threading.Lock:
        with self._lock:
            return self._sperren[token]

    def _laden(self, token: str) -> Dokument:
        with self._verbindung() as db:
            if db.execute("SELECT 1 FROM freigaben WHERE token = ?", (token,)).fetchone() is None:
                raise FreigabeFehler("Diese Freigabe gibt es nicht mehr.")
        datei = self._datei(token)
        if not datei.is_file():
            with self._verbindung() as db:
                db.execute("DELETE FROM freigaben WHERE token = ?", (token,))
            raise FreigabeFehler("Diese Freigabe gibt es nicht mehr.")
        return Dokument.laden(json.loads(datei.read_text(encoding="utf-8")))

    def _schreiben(self, token: str, dokument: Dokument, alarme: int) -> None:
        roh = json.dumps(dokument.sichern(), ensure_ascii=False).encode("utf-8")
        # Written beside the target and moved into place, so a crash mid-write cannot leave a
        # half-written document where a readable one used to be.
        vorlaeufig = self._datei(token).with_suffix(".json.neu")
        vorlaeufig.write_bytes(roh)
        vorlaeufig.replace(self._datei(token))
        with self._verbindung() as db:
            db.execute("UPDATE freigaben SET zuletzt = ?, alarme = ?, bytes = ? WHERE token = ?",
                       (_jetzt().isoformat(), alarme, len(roh), token))

    def anlegen(self, arbeitsmappe: dict) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        dokument = Dokument.aus_arbeitsmappe(arbeitsmappe)
        jetzt = _jetzt()
        with self._sperre(token):
            with self._verbindung() as db:
                db.execute(
                    "INSERT INTO freigaben (token, angelegt, zuletzt, alarme, bytes)"
                    " VALUES (?, ?, ?, 0, 0)",
                    (token, jetzt.isoformat(), jetzt.isoformat()))
            self._schreiben(token, dokument, len(arbeitsmappe.get("alarme", [])))
        return token, jetzt + timedelta(days=self._tage)

    def lesen(self, token: str) -> tuple[dict, datetime]:
        """Reading pushes the expiry out, so a link in use does not go away underneath anyone."""
        with self._sperre(token):
            dokument = self._laden(token)
            with self._verbindung() as db:
                db.execute("UPDATE freigaben SET zuletzt = ? WHERE token = ?",
                           (_jetzt().isoformat(), token))
            return dokument.arbeitsmappe(), _jetzt() + timedelta(days=self._tage)

    def stand(self, token: str, seit: int) -> dict:
        """What changed since the caller last heard, and where the document stands now."""
        with self._sperre(token):
            dokument = self._laden(token)
            with self._verbindung() as db:
                db.execute("UPDATE freigaben SET zuletzt = ? WHERE token = ?",
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
        with self._lock:
            self._datei(token).unlink(missing_ok=True)
            with self._verbindung() as db:
                return db.execute("DELETE FROM freigaben WHERE token = ?",
                                  (token,)).rowcount > 0

    def aufraeumen(self) -> int:
        """Drops everything unread for longer than the retention, file and row together."""
        grenze = (_jetzt() - timedelta(days=self._tage)).isoformat()
        with self._lock:
            with self._verbindung() as db:
                abgelaufen = [z[0] for z in db.execute(
                    "SELECT token FROM freigaben WHERE zuletzt < ?", (grenze,)).fetchall()]
                for token in abgelaufen:
                    self._datei(token).unlink(missing_ok=True)
                    db.execute("DELETE FROM freigaben WHERE token = ?", (token,))

            # A file without a row is orphaned - a crash between the write and the insert, or a
            # volume restored from elsewhere. Nothing can reach it, so it goes too.
            with self._verbindung() as db:
                bekannt = {z[0] for z in db.execute("SELECT token FROM freigaben").fetchall()}
            for datei in self._verzeichnis.glob("*.json.neu"):
                datei.unlink(missing_ok=True)
            for datei in self._verzeichnis.glob("*.json"):
                if datei.stem not in bekannt:
                    datei.unlink(missing_ok=True)
                    abgelaufen.append(datei.stem)
        return len(abgelaufen)

    def anzahl(self) -> int:
        with self._verbindung() as db:
            return db.execute("SELECT COUNT(*) FROM freigaben").fetchone()[0]
