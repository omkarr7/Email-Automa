import json
import re

from .router import Router

GENERIC_PATTERNS = [
    r"i am writing to express my interest",
    r"i was impressed by your innovative work",
    r"valuable addition to your team",
    r"passionate about leveraging",
    r"would love to explore opportunities",
    r"i believe my skills and experience",
]


def deterministic(
    body,
    company,
    person=None,
    vacancy_url=None,
    min_length=450,
    max_length=2200,
    require_company=True,
    require_person=True,
):
    errors = []
    text = (body or "").strip()
    if len(text) < min_length:
        errors.append("too_short")
    if len(text) > max_length:
        errors.append("too_long")
    if require_company and company.lower() not in text.lower():
        errors.append("company_missing")
    if require_person and person and person.lower() not in text.lower():
        errors.append("person_missing")
    if "{{" in text or "}}" in text:
        errors.append("unresolved_template")
    if vacancy_url and vacancy_url not in text:
        errors.append("verified_vacancy_url_missing")
    hits = sum(bool(re.search(pattern, text, re.I)) for pattern in GENERIC_PATTERNS)
    if hits >= 3:
        errors.append("generic_language")
    return errors


def _heuristic_review(email, company, person, approved_facts, profile):
    issues = deterministic(
        email,
        company,
        person,
        min_length=120,
        max_length=2200,
        require_company=True,
        require_person=bool(person),
    )
    unsupported_claims = []
    facts_text = " ".join(
        str(f.get("fact_text", "")) + " " + json.dumps(f.get("value", ""), ensure_ascii=False)
        for f in approved_facts
    ).lower()
    body = (email or "").lower()
    if "opening" in body and "current_vacancy" not in {f.get("fact_type") for f in approved_facts}:
        unsupported_claims.append("mentions_opening_without_verified_fact")

    company_relevance = 90 if company.lower() in body else 45
    person_relevance = 90 if person and person.lower() in body else 70
    candidate_fit = 80 if profile else 65
    specificity = 85 if approved_facts or facts_text else 60
    factuality = 95 if not unsupported_claims else 50
    genericity_risk = 20 if "i am writing to express my interest" not in body else 55

    return {
        "company_relevance": company_relevance,
        "person_relevance": person_relevance,
        "candidate_fit": candidate_fit,
        "specificity": specificity,
        "factuality": factuality,
        "genericity_risk": genericity_risk,
        "issues": issues,
        "unsupported_claims": unsupported_claims,
        "decision": "PASS" if not issues and not unsupported_claims else "REVISE",
    }


def critique(email, company, person, approved_facts, profile, router=None):
    router = router or Router()
    if not router.available("critic"):
        return _heuristic_review(email, company, person, approved_facts, profile)

    prompt = f"""
You are the final email quality gate. The email MUST NOT be sent unless it is
specific, factually grounded, and relevant to the particular person.

Return JSON:
{{
 "company_relevance": 0-100,
 "person_relevance": 0-100,
 "candidate_fit": 0-100,
 "specificity": 0-100,
 "factuality": 0-100,
 "genericity_risk": 0-100,
 "issues": ["..."],
 "unsupported_claims": ["..."],
 "decision": "PASS|REVISE|REJECT"
}}

PERSON: {person}
COMPANY: {company}
APPROVED FACTS: {json.dumps(approved_facts, ensure_ascii=False)}
CANDIDATE PROFILE: {json.dumps(profile, ensure_ascii=False)}
EMAIL:
{email}
"""
    result = router.call("critic", prompt, json_mode=True)
    return json.loads(result.text)


def passes(result, thresholds):
    return (
        result["decision"] == "PASS"
        and result["company_relevance"] >= thresholds["min_company_relevance"]
        and result["person_relevance"] >= thresholds["min_person_relevance"]
        and result["candidate_fit"] >= thresholds["min_candidate_fit"]
        and result["specificity"] >= thresholds["min_specificity"]
        and result["factuality"] >= thresholds["min_factuality"]
        and result["genericity_risk"] <= thresholds["max_genericity"]
        and not result.get("unsupported_claims")
    )
