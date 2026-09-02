import csv, hashlib, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "evidence.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    url TEXT NOT NULL,
    final_url TEXT,
    title TEXT,
    source_type TEXT,
    retrieved_at TEXT NOT NULL,
    http_status INTEGER,
    content_hash TEXT,
    content TEXT,
    UNIQUE(company, final_url, content_hash)
);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    fact_text TEXT NOT NULL,
    value_json TEXT,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence_ids TEXT NOT NULL,
    validated_at TEXT NOT NULL
);
"""

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c

def snapshot(c, company, source):
    content = source.get("source_text", "")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT OR IGNORE INTO evidence
        (company,url,final_url,title,source_type,retrieved_at,http_status,content_hash,content)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        company, source.get("source_url",""), source.get("source_url",""),
        source.get("source_title",""), source.get("source_type",""),
        now, source.get("http_status"), digest, content
    ))
    c.commit()
    row = c.execute(
        "SELECT id FROM evidence WHERE company=? AND final_url=? AND content_hash=?",
        (company, source.get("source_url",""), digest)
    ).fetchone()
    return row["id"]

def save_fact(c, company, fact, evidence_ids):
    c.execute("""
        INSERT INTO facts
        (company,fact_type,fact_text,value_json,status,confidence,evidence_ids,validated_at)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        company, fact["fact_type"], fact["fact_text"],
        json.dumps(fact.get("value"), ensure_ascii=False),
        fact["status"], fact["confidence"],
        json.dumps(evidence_ids),
        datetime.now(timezone.utc).isoformat()
    ))
    c.commit()


def evidence_ids_for_urls(c, company, urls):
    if not urls:
        return []
    placeholders = ",".join("?" for _ in urls)
    rows = c.execute(
        f"""
        SELECT id FROM evidence
        WHERE company=? AND final_url IN ({placeholders})
        ORDER BY id
        """,
        [company, *urls],
    ).fetchall()
    return [row["id"] for row in rows]
