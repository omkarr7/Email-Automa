import json
import os

from .config import profile, routing
from .nudge import run_nudges
from .outreach_db import approved_facts


def fact_loader(row):
    return approved_facts(row)


def thresholds():
    cfg = routing().get("quality") or {}
    return {
        "min_company_relevance": cfg.get("min_company_relevance", 75),
        "min_person_relevance": cfg.get("min_person_relevance", 75),
        "min_candidate_fit": cfg.get("min_candidate_fit", 75),
        "min_specificity": cfg.get("min_specificity", 70),
        "min_factuality": cfg.get("min_factuality", 90),
        "max_genericity": cfg.get("max_genericity", 30),
    }


def main():
    dry_run = os.getenv("DRY_RUN", "true").lower() != "false"
    results = run_nudges(
        fact_loader,
        profile(),
        thresholds(),
        dry_run=dry_run,
        limit=int(os.getenv("DAILY_NUDGE_LIMIT", "3")),
    )
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
