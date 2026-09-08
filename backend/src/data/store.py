import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from entities.alarm import Arbeitsmappe


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Session:
    id: str
    expires_at: datetime
    arbeitsmappe: Arbeitsmappe = field(default_factory=Arbeitsmappe)

    @property
    def seconds_left(self) -> int:
        return max(0, int((self.expires_at - _now()).total_seconds()))


class SessionStore:
    """
    Sessions live in memory and nowhere else. Nothing is written to disk, so a restart drops
    every session — which is the intent: the browser holds the authoritative copy and resends it.

    Every read pushes the expiry back, so a session dies only after the configured idle time.
    Endpoints run in a threadpool, hence the lock.
    """

    def __init__(self, ttl: timedelta):
        self._ttl = ttl
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        session = Session(id=secrets.token_urlsafe(24), expires_at=_now() + self._ttl)
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.expires_at <= _now():
                del self._sessions[session_id]
                return None
            session.expires_at = _now() + self._ttl
            return session

    def drop(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def sweep(self) -> int:
        with self._lock:
            expired = [key for key, s in self._sessions.items() if s.expires_at <= _now()]
            for key in expired:
                del self._sessions[key]
            return len(expired)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
