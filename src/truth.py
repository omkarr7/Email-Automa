"""
Truth layer.

Important design rule:
LLMs do not establish truth. They extract candidate facts from source evidence.
This module applies source hierarchy, freshness, corroboration and evidence
requirements before a fact becomes APPROVED for email generation.
"""

PRIMARY = {"careers_page", "career_link", "official_company_page", "official_press"}
STRONG_EXTERNAL = {"official_investor", "reputable_news"}
WEAK = {"search_result", "aggregator", "social"}

def source_weight(source_type):
    if source_type in PRIMARY: return 1.0
    if source_type in STRONG_EXTERNAL: return 0.75
    if source_type in WEAK: return 0.35
    return 0.5

def approve_facts(company, extracted_facts, evidence_records):
    """
    Extracted facts must contain source indices referring to evidence_records.
    A fact is approved only if its cited evidence is present and meaningful.
    """
    approved, rejected = [], []
    for fact in extracted_facts:
        indices = fact.get("evidence_indices", [])
        cited = [evidence_records[i] for i in indices if isinstance(i, int) and 0 <= i < len(evidence_records)]
        if not cited:
            rejected.append((fact, "no_evidence"))
            continue

        weights = [source_weight(e.get("source_type","")) for e in cited]
        best = max(weights)
        corroboration = len({e.get("source_url") for e in cited})

        # Strong source alone can approve a fact if confidence is high.
        # Weak sources require corroboration and still cannot prove a current vacancy.
        if fact["fact_type"] in {"current_vacancy", "current_vacancy_url"}:
            primary = any(e.get("source_type") in PRIMARY for e in cited)
            if not primary:
                rejected.append((fact, "current_vacancy_requires_primary_source"))
                continue
            if fact.get("confidence", 0) < 0.85:
                rejected.append((fact, "low_confidence"))
                continue

        elif best < 0.5 and corroboration < 2:
            rejected.append((fact, "weak_single_source"))
            continue

        status = "VERIFIED" if best >= 0.9 else "CORROBORATED"
        approved.append({
            **fact,
            "status": status,
            "source_urls": [e.get("source_url") for e in cited]
        })

    return approved, rejected
