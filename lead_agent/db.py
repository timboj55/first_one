"""SQLite persistence. One connection per thread; WAL mode; JSON columns for flexible blobs."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Iterable, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
  contact_id      TEXT PRIMARY KEY,
  status          TEXT NOT NULL DEFAULT 'active',
  lead            TEXT NOT NULL DEFAULT '{}',
  messages        TEXT NOT NULL DEFAULT '[]',
  timezone        TEXT,
  created_at      REAL NOT NULL,
  updated_at      REAL NOT NULL,
  last_inbound_at REAL,
  last_outbound_at REAL,
  sms_sent        INTEGER NOT NULL DEFAULT 0,
  calls_placed    INTEGER NOT NULL DEFAULT 0,
  cadence_index   INTEGER NOT NULL DEFAULT 0,
  cadence_kind    TEXT NOT NULL DEFAULT 'initial',
  outcome         TEXT,
  appointment_id  TEXT,
  ghl_conversation_id TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id TEXT NOT NULL,
  kind       TEXT NOT NULL,
  run_at     REAL NOT NULL,
  payload    TEXT NOT NULL DEFAULT '{}',
  status     TEXT NOT NULL DEFAULT 'pending',
  attempts   INTEGER NOT NULL DEFAULT 0,
  error      TEXT,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_due ON jobs(status, run_at);
CREATE TABLE IF NOT EXISTS events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id TEXT,
  ts         REAL NOT NULL,
  kind       TEXT NOT NULL,
  data       TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS events_contact ON events(contact_id, ts);
CREATE TABLE IF NOT EXISTS sent_messages (
  message_id TEXT PRIMARY KEY,
  contact_id TEXT NOT NULL,
  ts         REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS calls (
  call_id    TEXT PRIMARY KEY,
  contact_id TEXT NOT NULL,
  ts         REAL NOT NULL,
  status     TEXT,
  data       TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS seen_webhooks (
  key TEXT PRIMARY KEY,
  ts  REAL NOT NULL
);
"""

ACTIVE_STATUSES = ("active",)
TERMINAL_STATUSES = ("booked", "stopped", "opted_out", "not_interested", "handoff", "paused_human")


class Store:
    _mem_counter = 0

    def __init__(self, path: str = "lead_agent.sqlite3"):
        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._uri = False
        if path == ":memory:":
            # One shared in-memory DB across threads (each thread has its own connection).
            Store._mem_counter += 1
            path = f"file:lead_agent_mem_{id(self)}_{Store._mem_counter}?mode=memory&cache=shared"
            self._uri = True
        self.path = path
        self._anchor = self.conn()  # keeps a shared-cache memory DB alive
        with self._write_lock:
            self._anchor.executescript(SCHEMA)

    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, check_same_thread=False, uri=self._uri)
            c.row_factory = sqlite3.Row
            if not self._uri:
                c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=30000")
            self._local.conn = c
        return c

    # ---------- conversations ----------
    def get_conversation(self, contact_id: str) -> Optional[dict[str, Any]]:
        row = self.conn().execute("SELECT * FROM conversations WHERE contact_id=?", (contact_id,)).fetchone()
        return self._conv(row) if row else None

    def upsert_conversation(self, contact_id: str, lead: dict[str, Any], timezone: str | None) -> dict[str, Any]:
        now = time.time()
        with self._write_lock, self.conn() as c:
            c.execute(
                """INSERT INTO conversations(contact_id, lead, timezone, created_at, updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(contact_id) DO UPDATE SET lead=excluded.lead, timezone=COALESCE(excluded.timezone, conversations.timezone), updated_at=excluded.updated_at""",
                (contact_id, json.dumps(lead), timezone, now, now),
            )
        return self.get_conversation(contact_id)  # type: ignore[return-value]

    def update_conversation(self, contact_id: str, **fields: Any) -> None:
        if not fields:
            return
        if "messages" in fields and not isinstance(fields["messages"], str):
            fields["messages"] = json.dumps(fields["messages"])
        if "lead" in fields and not isinstance(fields["lead"], str):
            fields["lead"] = json.dumps(fields["lead"])
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._write_lock, self.conn() as c:
            c.execute(f"UPDATE conversations SET {cols} WHERE contact_id=?", (*fields.values(), contact_id))

    def bump(self, contact_id: str, column: str) -> None:
        with self._write_lock, self.conn() as c:
            c.execute(f"UPDATE conversations SET {column}={column}+1, updated_at=? WHERE contact_id=?", (time.time(), contact_id))

    def list_conversations(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        q = "SELECT * FROM conversations" + (" WHERE status=?" if status else "") + " ORDER BY updated_at DESC LIMIT ?"
        args: tuple = (status, limit) if status else (limit,)
        return [self._conv(r) for r in self.conn().execute(q, args).fetchall()]

    @staticmethod
    def _conv(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["lead"] = json.loads(d.get("lead") or "{}")
        d["messages"] = json.loads(d.get("messages") or "[]")
        return d

    # ---------- jobs ----------
    def schedule(self, contact_id: str, kind: str, run_at: float, payload: dict[str, Any] | None = None) -> int:
        with self._write_lock, self.conn() as c:
            cur = c.execute(
                "INSERT INTO jobs(contact_id, kind, run_at, payload, created_at) VALUES(?,?,?,?,?)",
                (contact_id, kind, run_at, json.dumps(payload or {}), time.time()),
            )
            return int(cur.lastrowid)

    def cancel_jobs(self, contact_id: str, kinds: Iterable[str] | None = None) -> int:
        with self._write_lock, self.conn() as c:
            if kinds:
                ks = list(kinds)
                cur = c.execute(
                    f"UPDATE jobs SET status='cancelled' WHERE contact_id=? AND status='pending' AND kind IN ({','.join('?'*len(ks))})",
                    (contact_id, *ks),
                )
            else:
                cur = c.execute("UPDATE jobs SET status='cancelled' WHERE contact_id=? AND status='pending'", (contact_id,))
            return cur.rowcount

    def pending_jobs(self, contact_id: str) -> list[dict[str, Any]]:
        rows = self.conn().execute(
            "SELECT * FROM jobs WHERE contact_id=? AND status='pending' ORDER BY run_at", (contact_id,)
        ).fetchall()
        return [self._job(r) for r in rows]

    def claim_due_jobs(self, now: float | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Atomically mark due jobs as running and return them."""
        now = now or time.time()
        with self._write_lock, self.conn() as c:
            rows = c.execute(
                "SELECT * FROM jobs WHERE status='pending' AND run_at<=? ORDER BY run_at LIMIT ?", (now, limit)
            ).fetchall()
            ids = [r["id"] for r in rows]
            if ids:
                c.execute(
                    f"UPDATE jobs SET status='running', attempts=attempts+1 WHERE id IN ({','.join('?'*len(ids))})", ids
                )
        return [self._job(r) for r in rows]

    def finish_job(self, job_id: int, ok: bool, error: str | None = None, retry_at: float | None = None) -> None:
        with self._write_lock, self.conn() as c:
            if ok:
                c.execute("UPDATE jobs SET status='done', error=NULL WHERE id=?", (job_id,))
            elif retry_at is not None:
                c.execute("UPDATE jobs SET status='pending', run_at=?, error=? WHERE id=?", (retry_at, error, job_id))
            else:
                c.execute("UPDATE jobs SET status='failed', error=? WHERE id=?", (error, job_id))

    @staticmethod
    def _job(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["payload"] = json.loads(d.get("payload") or "{}")
        return d

    # ---------- events / audit ----------
    def log(self, contact_id: str | None, kind: str, **data: Any) -> None:
        with self._write_lock, self.conn() as c:
            c.execute(
                "INSERT INTO events(contact_id, ts, kind, data) VALUES(?,?,?,?)",
                (contact_id, time.time(), kind, json.dumps(data, default=str)),
            )

    def events(self, contact_id: str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn().execute(
            "SELECT * FROM events WHERE contact_id=? ORDER BY ts DESC LIMIT ?", (contact_id, limit)
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data"])
            out.append(d)
        return out

    # ---------- sent messages (to tell our SMS from a human's) ----------
    def record_sent(self, message_id: str, contact_id: str) -> None:
        if not message_id:
            return
        with self._write_lock, self.conn() as c:
            c.execute("INSERT OR IGNORE INTO sent_messages(message_id, contact_id, ts) VALUES(?,?,?)", (message_id, contact_id, time.time()))

    def sent_by_us(self, message_id: str) -> bool:
        return self.conn().execute("SELECT 1 FROM sent_messages WHERE message_id=?", (message_id,)).fetchone() is not None

    # ---------- calls ----------
    def record_call(self, call_id: str, contact_id: str, status: str, data: dict[str, Any] | None = None) -> None:
        with self._write_lock, self.conn() as c:
            c.execute(
                """INSERT INTO calls(call_id, contact_id, ts, status, data) VALUES(?,?,?,?,?)
                   ON CONFLICT(call_id) DO UPDATE SET status=excluded.status, data=excluded.data""",
                (call_id, contact_id, time.time(), status, json.dumps(data or {}, default=str)),
            )

    def get_call(self, call_id: str) -> Optional[dict[str, Any]]:
        r = self.conn().execute("SELECT * FROM calls WHERE call_id=?", (call_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["data"] = json.loads(d["data"])
        return d

    # ---------- settings ----------
    def get_setting(self, key: str, default: str | None = None) -> Optional[str]:
        r = self.conn().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default

    def set_setting(self, key: str, value: str) -> None:
        with self._write_lock, self.conn() as c:
            c.execute("INSERT INTO settings(key, value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    # ---------- webhook de-dup ----------
    def seen_webhook(self, key: str, ttl_seconds: int = 6 * 3600) -> bool:
        """Return True if this key was already processed recently; records it otherwise."""
        now = time.time()
        with self._write_lock, self.conn() as c:
            c.execute("DELETE FROM seen_webhooks WHERE ts < ?", (now - ttl_seconds,))
            r = c.execute("SELECT 1 FROM seen_webhooks WHERE key=?", (key,)).fetchone()
            if r:
                return True
            c.execute("INSERT INTO seen_webhooks(key, ts) VALUES(?,?)", (key, now))
            return False
