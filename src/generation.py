import json

from .router import Router

SYSTEM = """
Write one concise professional outreach email.

Hard rules:
- Use ONLY approved facts.
- Do not add unsupported claims.
- Do not claim a vacancy exists unless the approved facts include a verified current vacancy.
- Address the specific person's designation/context.
- Do not use generic flattery.
- Do not mention research that is not in the approved facts.
- Sound like a real candidate, not a marketing sequence.
- The candidate facts are authoritative and must not be embellished.
- Return JSON with subject and body.
"""


def _deterministic_generate(context, approved_facts):
    company = context["company"]["company"]
    person = context["recipient"]
    candidate = context["candidate"]
    vacancy = next((f.get("value") for f in approved_facts if f.get("fact_type") == "current_vacancy"), None)
    reason = next((f.get("fact_text") for f in approved_facts if f.get("fact_type") == "company_context"), "")

    if isinstance(vacancy, dict) and vacancy.get("job_title") and vacancy.get("job_url"):
        subject = f"Exploring {vacancy['job_title']} at {company} - {candidate['name']}"
        body = (
            f"Hello {person},\n\n"
            f"I'm {candidate['name']}, and I wanted to introduce myself regarding opportunities at {company}. "
            f"I noticed the {vacancy['job_title']} role ({vacancy['job_url']}) and thought my background across "
            "data governance, data quality, Python, SQL, analytics and machine learning could be relevant.\n\n"
            f"{reason}\n\n"
            "If it would be helpful, I would be glad to share any additional context.\n\n"
            f"Best regards,\n{candidate['name']}"
        )
        return {"subject": subject, "body": body}

    subject = f"Exploring data and AI opportunities at {company} - {candidate['name']}"
    body = (
        f"Hello {person},\n\n"
        f"I'm {candidate['name']}, and I wanted to introduce myself regarding opportunities at {company}. "
        "My background is strongest across data governance, data quality, Python, SQL, analytics and machine learning.\n\n"
        f"{reason}\n\n"
        "I was not able to verify a current role that closely matches my background, so I wanted to reach out directly "
        "without implying an opening that I could not confirm.\n\n"
        f"Best regards,\n{candidate['name']}"
    )
    return {"subject": subject, "body": body}


def generate(context, approved_facts, router=None):
    router = router or Router()
    if not router.available("generation"):
        return _deterministic_generate(context, approved_facts)

    prompt = SYSTEM + "\nCONTEXT:\n" + json.dumps(
        {
            "person": context["recipient"],
            "company": context["company"],
            "approved_facts": approved_facts,
            "candidate": context["candidate"],
        },
        ensure_ascii=False,
    )
    result = router.call("generation", prompt, json_mode=True)
    return json.loads(result.text)
