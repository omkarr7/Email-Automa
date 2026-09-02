import os, json
from google import genai
from google.genai import types

SYSTEM = """
You are a careful job-outreach research assistant.
Your job is to produce STRUCTURED facts for an email template, not a free-form email.

Rules:
- Never invent a job, hiring activity, funding, employee, technology, or company fact.
- If the evidence is insufficient, say so.
- Distinguish a currently advertised vacancy from a general hiring signal.
- A vacancy counts as CURRENT only when the supplied evidence clearly indicates the role is currently open.
- Do not infer that a company is hiring merely because it is a startup or recently funded.
- Keep claims directly supported by the supplied source snippets/URLs.
- Never claim the candidate has experience that is not in the supplied profile.
Return valid JSON only.
"""

def client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return genai.Client(api_key=key)

def analyse_company(company, jobs, profile):
    payload = {
        "company": company,
        "candidate_profile": profile,
        "candidate_jobs": jobs,
    }
    prompt = SYSTEM + "\nAnalyse this company/job data:\n" + json.dumps(payload, ensure_ascii=False)

    response = client().models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "vacancy_status": {
                        "type": "string",
                        "enum": ["CURRENT", "NOT_CURRENT", "UNKNOWN"]
                    },
                    "best_job_index": {"type": "integer"},
                    "company_reason": {"type": "string"},
                    "candidate_fit": {"type": "string"},
                    "relevant_area": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence_notes": {"type": "array", "items": {"type": "string"}},
                    "safe_to_contact": {"type": "boolean"}
                },
                "required": [
                    "vacancy_status", "best_job_index", "company_reason",
                    "candidate_fit", "relevant_area", "confidence",
                    "evidence_notes", "safe_to_contact"
                ]
            }
        )
    )
    return json.loads(response.text)
