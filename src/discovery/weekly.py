import json
from datetime import datetime, timezone
from .models import CompanyCandidate
from .normalizer import normalize_candidate
from .validator import validate_candidate
from .deduplicator import is_duplicate
from .db import start_run, finish_run, existing_companies, upsert_company, add_source
from .scorer import score_company, priority
from .sources.web_search import discover

DEFAULT_QUERIES = [
    "AI startups Bengaluru India hiring data science machine learning",
    "data science startups Bengaluru India hiring",
    "analytics startups Bengaluru India hiring",
    "AI startups Mumbai India hiring data science machine learning",
    "data science startups Mumbai India hiring",
    "analytics startups Mumbai India hiring",
    "AI startups Pune India hiring data science machine learning",
    "data science startups Pune India hiring",
    "analytics startups Pune India hiring",
]

def run(queries=None):
    run_id=start_run()
    queries=queries or DEFAULT_QUERIES
    candidates=discover(queries)
    existing=existing_companies()

    stats={"candidates_found":len(candidates),"new_companies":0,"duplicates":0,"validated":0,"rejected":0}

    for raw in candidates:
        if isinstance(raw, dict):
            raw=CompanyCandidate(**raw)

        candidate=normalize_candidate(raw)
        valid, errors=validate_candidate(candidate)
        if not valid:
            stats["rejected"]+=1
            continue

        duplicate, reason=is_duplicate(candidate, existing)
        if duplicate:
            stats["duplicates"]+=1
            continue

        score=score_company(candidate)
        row=upsert_company(candidate, score=score)
        add_source(row["id"], candidate.source, candidate.source_url)
        existing=existing_companies()
        stats["new_companies"]+=1
        stats["validated"]+=1

    finish_run(run_id, **stats)
    return {"run_id":run_id,"priority_counts":priority_counts(),"stats":stats}

def priority_counts():
    from .db import connect
    c=connect()
    rows=c.execute("""
      SELECT
        CASE WHEN discovery_score>=80 THEN 'HIGH'
             WHEN discovery_score>=60 THEN 'MEDIUM'
             ELSE 'LOW' END AS priority,
        COUNT(*) AS count
      FROM companies
      GROUP BY priority
    """).fetchall()
    return {r["priority"]:r["count"] for r in rows}

if __name__=="__main__":
    print(json.dumps(run(), indent=2))
