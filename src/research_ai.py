import json
import os
import re

ROLE_PATTERNS = [
    "data engineer",
    "data scientist",
    "analytics engineer",
    "data analyst",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "product analyst",
    "data operations",
    "business intelligence",
]

CURRENT_TERMS = ["apply", "job", "jobs", "opening", "open role", "vacancy", "position", "hiring"]
STALE_TERMS = ["closed", "expired", "filled", "archived", "inactive"]

SYSTEM = """
You are a source-grounded research extractor.

Do NOT decide whether a claim is true.
Extract candidate facts ONLY from the supplied evidence.
Every fact MUST cite one or more evidence indices.
If the evidence does not support a fact, do not output it.
Do not infer growth, funding, hiring intent, company culture, leadership,
or job status from vague language.

Return JSON only.
"""


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _infer_role(text):
    blob = (text or "").lower()
    for role in ROLE_PATTERNS:
        if role in blob:
            return role.title()
    return ""


def _deterministic_extract(company, evidence):
    facts = []
    for idx, item in enumerate(evidence[:40]):
        title = item.get("source_title", "")
        url = item.get("source_url", "")
        text = item.get("source_text", "")[:4000]
        source_type = item.get("source_type", "")
        blob = f"{title}\n{text}\n{url}".lower()

        if source_type in {"careers_page", "career_link"}:
            facts.append(
                {
                    "fact_type": "careers_page",
                    "fact_text": f"Public careers page found for {company['company']}",
                    "value": url,
                    "confidence": 0.95,
                    "evidence_indices": [idx],
                }
            )

        if any(term in blob for term in CURRENT_TERMS) and not any(term in blob for term in STALE_TERMS):
            role = _infer_role(blob)
            if role and url.startswith(("http://", "https://")):
                facts.append(
                    {
                        "fact_type": "current_vacancy",
                        "fact_text": f"{role} appears to be currently listed for {company['company']}",
                        "value": {
                            "job_title": role,
                            "job_url": url,
                            "location": company.get("city", ""),
                            "description": _clean(title or text[:280]),
                        },
                        "confidence": 0.9 if source_type in {"careers_page", "career_link"} else 0.8,
                        "evidence_indices": [idx],
                    }
                )
    return facts


def extract(company, evidence):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return _deterministic_extract(company, evidence)

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return _deterministic_extract(company, evidence)

    client = genai.Client(api_key=key)
    payload = {"company": company, "evidence": evidence[:40]}
    response = client.models.generate_content(
        model=os.getenv("GEMINI_RESEARCH_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
        contents=SYSTEM + "\nINPUT:\n" + json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "facts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fact_type": {"type": "string"},
                                "fact_text": {"type": "string"},
                                "value": {"type": "string"},
                                "confidence": {"type": "number"},
                                "evidence_indices": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                },
                            },
                            "required": ["fact_type", "fact_text", "confidence", "evidence_indices"],
                        },
                    }
                },
                "required": ["facts"],
            },
        ),
    )
    return json.loads(response.text)["facts"]
