import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "outreach.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS outreach (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 company TEXT NOT NULL,
 contact_name TEXT,
 contact_email TEXT NOT NULL,
 contact_designation TEXT,
 job_title TEXT,
 email_type TEXT NOT NULL DEFAULT 'initial',
 subject TEXT NOT NULL,
 body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 status TEXT NOT NULL DEFAULT 'prepared',
 thread_id TEXT,
 message_id TEXT,
 initial_message_id TEXT,
 sent_at TEXT,
 initial_sent_at TEXT,
 last_checked_at TEXT,
 reply_status TEXT DEFAULT 'NO_REPLY',
 reply_detected INTEGER NOT NULL DEFAULT 0,
 reply_message_id TEXT,
 reply_received_at TEXT,
 nudge_count INTEGER NOT NULL DEFAULT 0,
 nudge_sent INTEGER NOT NULL DEFAULT 0,
 next_nudge_at TEXT,
 last_nudge_message_id TEXT,
 outreach_score REAL DEFAULT 0,
 personalisation_confidence REAL DEFAULT 0,
 approved_facts_json TEXT DEFAULT '[]',
 evidence_ids_json TEXT DEFAULT '[]',
 original_email_json TEXT DEFAULT '{}'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_contact_subject
ON outreach(contact_email, subject);

CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 outreach_id INTEGER,
 event_type TEXT NOT NULL,
 details TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn):
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(outreach)").fetchall()}
    additions = {
        "contact_name": "TEXT",
        "contact_designation": "TEXT",
        "job_title": "TEXT",
        "email_type": "TEXT NOT NULL DEFAULT 'initial'",
        "subject": "TEXT NOT NULL DEFAULT ''",
        "body": "TEXT NOT NULL DEFAULT ''",
        "created_at": "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "status": "TEXT NOT NULL DEFAULT 'prepared'",
        "thread_id": "TEXT",
        "message_id": "TEXT",
        "initial_message_id": "TEXT",
        "sent_at": "TEXT",
        "initial_sent_at": "TEXT",
        "last_checked_at": "TEXT",
        "reply_status": "TEXT DEFAULT 'NO_REPLY'",
        "reply_detected": "INTEGER NOT NULL DEFAULT 0",
        "reply_message_id": "TEXT",
        "reply_received_at": "TEXT",
        "nudge_count": "INTEGER NOT NULL DEFAULT 0",
        "nudge_sent": "INTEGER NOT NULL DEFAULT 0",
        "next_nudge_at": "TEXT",
        "last_nudge_message_id": "TEXT",
        "outreach_score": "REAL DEFAULT 0",
        "personalisation_confidence": "REAL DEFAULT 0",
        "approved_facts_json": "TEXT DEFAULT '[]'",
        "evidence_ids_json": "TEXT DEFAULT '[]'",
        "original_email_json": "TEXT DEFAULT '{}'",
    }
    for name, definition in additions.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE outreach ADD COLUMN {name} {definition}")

    conn.execute(
        "UPDATE outreach SET email_type=COALESCE(NULLIF(email_type,''), 'initial')"
    )
    conn.execute(
        "UPDATE outreach SET status='prepared' WHERE status IS NULL OR status=''"
    )
    conn.execute(
        """
        UPDATE outreach
        SET initial_sent_at=COALESCE(initial_sent_at, sent_at),
            sent_at=COALESCE(sent_at, initial_sent_at),
            initial_message_id=COALESCE(initial_message_id, message_id),
            message_id=COALESCE(message_id, initial_message_id),
            reply_status=CASE
                WHEN COALESCE(reply_status, '') <> '' THEN reply_status
                WHEN reply_detected=1 THEN 'REPLIED_NEUTRAL'
                ELSE 'NO_REPLY'
            END,
            nudge_count=CASE WHEN nudge_sent=1 AND nudge_count=0 THEN 1 ELSE nudge_count END
        """
    )
    conn.execute(
        """
        UPDATE outreach
        SET next_nudge_at=CASE
            WHEN next_nudge_at IS NOT NULL THEN next_nudge_at
            WHEN COALESCE(initial_sent_at, sent_at) IS NOT NULL
                 THEN datetime(COALESCE(initial_sent_at, sent_at), '+5 days')
            ELSE next_nudge_at
        END
        WHERE lower(status)='sent'
        """
    )
    conn.commit()


def _json_dump(value, fallback):
    return json.dumps(value if value is not None else fallback, ensure_ascii=False)


def _json_load(raw, fallback):
    try:
        return json.loads(raw or fallback)
    except Exception:
        return json.loads(fallback)


def already_contacted(conn, email):
    return conn.execute(
        "SELECT 1 FROM outreach WHERE lower(contact_email)=lower(?) LIMIT 1",
        (email,),
    ).fetchone() is not None


def insert_prepared(
    conn,
    *,
    company,
    contact_email,
    contact_name="",
    contact_designation="",
    job_title="",
    email_type="initial",
    subject,
    body,
    outreach_score=0,
    personalisation_confidence=0,
    approved_facts=None,
    evidence_ids=None,
    original_email=None,
):
    original_email = original_email or {"subject": subject, "body": body}
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO outreach
        (company, contact_name, contact_email, contact_designation, job_title,
         email_type, subject, body, status, outreach_score,
         personalisation_confidence, approved_facts_json, evidence_ids_json,
         original_email_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'prepared', ?, ?, ?, ?, ?)
        """,
        (
            company,
            contact_name,
            contact_email,
            contact_designation,
            job_title,
            email_type,
            subject,
            body,
            outreach_score,
            personalisation_confidence,
            _json_dump(approved_facts, []),
            _json_dump(evidence_ids, []),
            _json_dump(original_email, {}),
        ),
    )
    conn.commit()
    return cur.lastrowid


def prepared_rows(conn, email_type="initial"):
    return conn.execute(
        """
        SELECT * FROM outreach
        WHERE lower(status)='prepared' AND lower(email_type)=lower(?)
        ORDER BY id
        """,
        (email_type,),
    ).fetchall()


def mark_sent(conn, row_id, message_id, thread_id=None, sent_at=None, nudge_after_days=5):
    sent_at = sent_at or _utcnow()
    next_nudge_at = (
        datetime.fromisoformat(sent_at.replace("Z", "+00:00")) + timedelta(days=nudge_after_days)
    ).isoformat()
    conn.execute(
        """
        UPDATE outreach
        SET status='sent',
            message_id=?,
            initial_message_id=COALESCE(initial_message_id, ?),
            thread_id=COALESCE(?, thread_id),
            sent_at=?,
            initial_sent_at=COALESCE(initial_sent_at, ?),
            next_nudge_at=COALESCE(next_nudge_at, ?)
        WHERE id=?
        """,
        (message_id, message_id, thread_id, sent_at, sent_at, next_nudge_at, row_id),
    )
    conn.commit()


def register_sent(
    company,
    name,
    email,
    designation,
    thread_id,
    message_id,
    sent_at=None,
    nudge_after_days=5,
    approved_facts=None,
    evidence_ids=None,
    original_email=None,
):
    conn = connect()
    sent_at = sent_at or _utcnow()
    next_at = (
        datetime.fromisoformat(sent_at.replace("Z", "+00:00")) + timedelta(days=nudge_after_days)
    ).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO outreach
        (company, contact_name, contact_email, contact_designation, email_type,
         subject, body, status, thread_id, message_id, initial_message_id,
         sent_at, initial_sent_at, next_nudge_at, approved_facts_json,
         evidence_ids_json, original_email_json)
        VALUES (?, ?, ?, ?, 'initial', ?, ?, 'sent', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company,
            name,
            email,
            designation,
            (original_email or {}).get("subject", ""),
            (original_email or {}).get("body", ""),
            thread_id,
            message_id,
            message_id,
            sent_at,
            sent_at,
            next_at,
            _json_dump(approved_facts, []),
            _json_dump(evidence_ids, []),
            _json_dump(original_email, {}),
        ),
    )
    conn.commit()
    return conn.execute(
        """
        SELECT * FROM outreach
        WHERE contact_email=? AND company=? AND message_id=?
        """,
        (email, company, message_id),
    ).fetchone()


def approved_facts(row):
    return _json_load(row["approved_facts_json"], "[]")


def evidence_ids(row):
    return _json_load(row["evidence_ids_json"], "[]")


def original_email(row):
    return _json_load(row["original_email_json"], "{}")


def mark_reply(row_id, status, message_id=None, received_at=None):
    conn = connect()
    conn.execute(
        """
        UPDATE outreach
        SET reply_status=?,
            reply_detected=1,
            reply_message_id=?,
            reply_received_at=?,
            last_checked_at=?,
            status=lower(?)
        WHERE id=?
        """,
        (status, message_id, received_at, _utcnow(), status, row_id),
    )
    conn.commit()


def mark_checked(row_id):
    conn = connect()
    conn.execute(
        "UPDATE outreach SET last_checked_at=? WHERE id=?",
        (_utcnow(), row_id),
    )
    conn.commit()


def due_for_nudge(limit=None):
    conn = connect()
    sql = """
        SELECT * FROM outreach
        WHERE lower(status)='sent'
          AND reply_status='NO_REPLY'
          AND nudge_count < 1
          AND next_nudge_at IS NOT NULL
          AND next_nudge_at <= ?
        ORDER BY COALESCE(initial_sent_at, sent_at, created_at)
    """
    params = [_utcnow()]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def mark_nudge_sent(row_id, message_id):
    conn = connect()
    conn.execute(
        """
        UPDATE outreach
        SET nudge_count=nudge_count+1,
            nudge_sent=1,
            last_nudge_message_id=?,
            status='nudged',
            last_checked_at=?
        WHERE id=?
        """,
        (message_id, _utcnow(), row_id),
    )
    conn.commit()
