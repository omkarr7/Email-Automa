import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "outreach.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 canonical_name TEXT NOT NULL,
 normalized_name TEXT NOT NULL,
 domain TEXT,
 website TEXT,
 linkedin_url TEXT,
 city TEXT,
 industry TEXT,
 company_stage TEXT,
 employee_range TEXT,
 status TEXT DEFAULT 'DISCOVERED',
 discovery_score REAL DEFAULT 0,
 first_discovered_at TEXT NOT NULL,
 last_seen_at TEXT NOT NULL,
 last_researched_at TEXT,
 discovery_reason TEXT,
 UNIQUE(normalized_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_company_domain
ON companies(domain) WHERE domain IS NOT NULL AND domain <> '';

CREATE TABLE IF NOT EXISTS company_sources (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 company_id INTEGER NOT NULL,
 source TEXT NOT NULL,
 source_url TEXT,
 discovered_at TEXT NOT NULL,
 FOREIGN KEY(company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS discovery_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 started_at TEXT NOT NULL,
 finished_at TEXT,
 candidates_found INTEGER DEFAULT 0,
 new_companies INTEGER DEFAULT 0,
 duplicates INTEGER DEFAULT 0,
 validated INTEGER DEFAULT 0,
 rejected INTEGER DEFAULT 0,
 status TEXT DEFAULT 'RUNNING'
);
"""

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c

def start_run():
    c = connect()
    now = datetime.now(timezone.utc).isoformat()
    cur = c.execute("INSERT INTO discovery_runs(started_at) VALUES(?)", (now,))
    c.commit()
    return cur.lastrowid

def finish_run(run_id, **stats):
    c = connect()
    fields = ["finished_at=?","status='COMPLETED'"]
    values = [datetime.now(timezone.utc).isoformat()]
    for key in ["candidates_found","new_companies","duplicates","validated","rejected"]:
        if key in stats:
            fields.append(f"{key}=?")
            values.append(stats[key])
    values.append(run_id)
    c.execute(f"UPDATE discovery_runs SET {','.join(fields)} WHERE id=?", values)
    c.commit()

def existing_companies():
    return connect().execute("SELECT * FROM companies").fetchall()

def upsert_company(candidate, score=0):
    c = connect()
    now = datetime.now(timezone.utc).isoformat()
    norm = candidate.name.lower().strip()
    cur = c.execute("""
      INSERT INTO companies(
        canonical_name,normalized_name,domain,website,linkedin_url,city,industry,
        status,discovery_score,first_discovered_at,last_seen_at,discovery_reason
      ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(normalized_name) DO UPDATE SET
        last_seen_at=excluded.last_seen_at,
        website=COALESCE(companies.website, excluded.website),
        domain=COALESCE(companies.domain, excluded.domain),
        linkedin_url=COALESCE(companies.linkedin_url, excluded.linkedin_url)
    """, (
        candidate.name,norm,candidate.domain,candidate.website,candidate.linkedin_url,
        candidate.city,candidate.industry,"DISCOVERED",score,now,now,candidate.discovery_reason
    ))
    c.commit()
    row=c.execute("SELECT * FROM companies WHERE normalized_name=?", (norm,)).fetchone()
    return row

def add_source(company_id, source, source_url):
    c=connect()
    c.execute("""INSERT INTO company_sources(company_id,source,source_url,discovered_at)
                 VALUES(?,?,?,?)""",
              (company_id,source,source_url,datetime.now(timezone.utc).isoformat()))
    c.commit()
