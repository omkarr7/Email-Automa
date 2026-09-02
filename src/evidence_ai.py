import json
import os
import re

ROLE_TERMS = [
    "data engineer",
    "data scientist",
    "analytics engineer",
    "data analyst",
    "ml engineer",
    "machine learning engineer",
    "ai engineer",
    "product analyst",
]

CURRENT_TERMS = ["apply", "job", "jobs", "opening", "position", "vacancy", "hiring"]
STALE_TERMS = ["closed", "expired", "filled", "inactive", "archived"]

SYSTEM = """
You classify public job evidence for a candidate outreach workflow.

You receive:
- company information
- candidate profile
- public web evidence collected at a specific timestamp

Return JSON only.

Rules:
1. CURRENT means the evidence clearly indicates a currently open job.
2. NOT_CURRENT means the evidence clearly indicates no relevant current vacancy,
   or the page is historical/closed/expired.
3. UNKNOWN means the evidence is insufficient or ambiguous.
4. Never infer CURRENT simply because a company is a startup, funded, expanding,
   or generally hiring.
5. Never invent a job title, location, requirement, hiring manager, or company fact.
6. A search-result snippet alone is weak evidence. Prefer the actual job/careers page.
7. Identify the strongest evidence URL(s).
8. Candidate fit must be grounded only in the candidate profile.
9. If there is no current vacancy, produce a safe reason for a speculative
   outreach email without claiming a vacancy exists.
"""


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _candidate_fit(profile):
    areas = []
    for section in ("skills", "experience"):
        value = profile.get(section, {})
        if isinstance(value, dict):
            for items in value.values():
                if isinstance(items, list):
                    areas.extend(str(item) for item in items[:4])
                elif isinstance(items, dict):
                    areas.extend(str(item) for item in items.get("areas", [])[:4])
    return ", ".join(areas[:4]) or "data, analytics, Python and SQL"


def _role_from_text(text):
    blob = (text or "").lower()
    for term in ROLE_TERMS:
        if term in blob:
            return term.title()
    return ""


def _fallback(company, evidence, profile):
    strongest = []
    notes = []
    for item in evidence[:30]:
        title = item.get("source_title", "")
        url = item.get("source_url", "")
        text = item.get("source_text", "")[:5000]
        blob = f"{title}\n{text}\n{url}".lower()
        if any(term in blob for term in CURRENT_TERMS) and not any(term in blob for term in STALE_TERMS):
            role = _role_from_text(blob)
            if role and item.get("source_type") in {"careers_page", "career_link"}:
                strongest.append((role, url, title))

    if strongest:
        role, url, title = strongest[0]
        notes.append(f"Primary careers evidence suggests a current {role} opening.")
        return {
            "vacancy_status": "CURRENT",
            "job_title": role,
            "job_url": url,
            "location": company.get("city", ""),
            "job_summary": _clean(title),
            "company_reason": company.get("current_signal") or f"your work in {company.get('domain', 'data and AI')}",
            "candidate_fit": _candidate_fit(profile),
            "relevant_area": company.get("domain", "data and AI"),
            "confidence": 0.88,
            "evidence_urls": [url],
            "evidence_notes": notes,
            "safe_to_contact": True,
        }

    reason = company.get("current_signal") or f"your work in {company.get('domain', 'data and AI')}"
    urls = [item.get("source_url", "") for item in evidence[:3] if item.get("source_url")]
    if urls:
        notes.append("Public company or careers evidence was found, but no verified current role was established.")

    return {
        "vacancy_status": "UNKNOWN" if urls else "NOT_CURRENT",
        "job_title": "",
        "job_url": "",
        "location": company.get("city", ""),
        "job_summary": "",
        "company_reason": reason,
        "candidate_fit": _candidate_fit(profile),
        "relevant_area": company.get("domain", "data and AI"),
        "confidence": 0.7 if urls else 0.6,
        "evidence_urls": urls,
        "evidence_notes": notes,
        "safe_to_contact": bool(urls or company.get("current_signal")),
    }


def classify(company, evidence, profile):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return _fallback(company, evidence, profile)

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return _fallback(company, evidence, profile)

    client = genai.Client(api_key=key)
    payload = {
        "company": company,
        "candidate_profile": profile,
        "evidence": evidence[:30],
    }

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=SYSTEM + "\nINPUT:\n" + json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "vacancy_status": {
                        "type": "string",
                        "enum": ["CURRENT", "NOT_CURRENT", "UNKNOWN"],
                    },
                    "job_title": {"type": "string"},
                    "job_url": {"type": "string"},
                    "location": {"type": "string"},
                    "job_summary": {"type": "string"},
                    "company_reason": {"type": "string"},
                    "candidate_fit": {"type": "string"},
                    "relevant_area": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_urls": {"type": "array", "items": {"type": "string"}},
                    "evidence_notes": {"type": "array", "items": {"type": "string"}},
                    "safe_to_contact": {"type": "boolean"},
                },
                "required": [
                    "vacancy_status",
                    "job_title",
                    "job_url",
                    "location",
                    "job_summary",
                    "company_reason",
                    "candidate_fit",
                    "relevant_area",
                    "confidence",
                    "evidence_urls",
                    "evidence_notes",
                    "safe_to_contact",
                ],
            },
        ),
    )
    return json.loads(response.text)
