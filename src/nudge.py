import json

from .email_quality import critique, deterministic, passes
from .gmail import send_message
from .outreach_db import due_for_nudge, evidence_ids, mark_nudge_sent
from .router import Router


def _deterministic_nudge_email(row, facts, candidate_profile):
    fit = "data, analytics, Python and SQL"
    skills = candidate_profile.get("skills", {})
    if isinstance(skills, dict):
        flat = []
        for items in skills.values():
            flat.extend(str(item) for item in items[:2])
        if flat:
            fit = ", ".join(flat[:4])

    fact_line = ""
    for fact in facts:
        if fact.get("fact_type") == "current_vacancy":
            value = fact.get("value") or {}
            title = value.get("job_title") or fact.get("fact_text", "")
            fact_line = f" If the {title} opening is still active, I would be glad to share any extra context."
            break

    subject = "Re: " + row["subject"].replace("Re: ", "")
    body = (
        f"Hello {row['contact_name'] or 'there'},\n\n"
        f"Following up on my earlier note about opportunities at {row['company']}. "
        f"My background remains strongest across {fit}.{fact_line}\n\n"
        "If there is a better person or team to reach out to, I would appreciate the direction.\n\n"
        "Best regards,\n"
        "Omkar Pawar"
    )
    return {"subject": subject, "body": body}


def generate_nudge(row, facts, candidate_profile, thresholds):
    router = Router()
    email = None
    if router.available("generation"):
        prompt = f"""Write a short, natural follow-up to a cold outreach email that has received no reply.

Hard rules:
- Do not say or imply the recipient read the first email.
- Do not add any company, person, vacancy, funding, hiring or product claims.
- Use ONLY APPROVED FACTS below.
- Do not repeat the original email.
- Keep it under 120 words.
- Do not use generic flattery.
- Return JSON only: {{"subject":"...","body":"..."}}

PERSON: {row['contact_name']}
DESIGNATION: {row['contact_designation']}
COMPANY: {row['company']}
APPROVED FACTS: {json.dumps(facts, ensure_ascii=False)}
ORIGINAL EMAIL: {json.dumps(json.loads(row['original_email_json'] or '{}'), ensure_ascii=False)}
CANDIDATE: {json.dumps(candidate_profile, ensure_ascii=False)}
"""
        result = router.call("generation", prompt, json_mode=True)
        email = json.loads(result.text)
    else:
        email = _deterministic_nudge_email(row, facts, candidate_profile)

    errors = deterministic(
        email.get("body", ""),
        row["company"],
        row["contact_name"],
        min_length=60,
        max_length=800,
        require_company=True,
        require_person=False,
    )
    if errors:
        return {"status": "REJECT", "errors": errors}

    review = critique(
        email["body"],
        row["company"],
        row["contact_name"],
        facts,
        candidate_profile,
        router if router.available("critic") else None,
    )
    return {
        "status": "PASS" if passes(review, thresholds) else "REJECT",
        "email": email,
        "review": review,
    }


def run_nudges(fact_loader, candidate_profile, thresholds, dry_run=True, limit=None):
    results = []
    for row in due_for_nudge(limit=limit):
        facts = fact_loader(row)

        if not facts:
            results.append({"id": row["id"], "status": "REJECT", "reason": "no_approved_facts"})
            continue

        result = generate_nudge(row, facts, candidate_profile, thresholds)
        if result["status"] != "PASS":
            results.append({"id": row["id"], "status": "REJECT", "detail": result})
            continue

        if dry_run:
            results.append(
                {
                    "id": row["id"],
                    "status": "DRY_RUN",
                    "email": result["email"],
                    "evidence_ids": evidence_ids(row),
                }
            )
            continue

        sent = send_message(
            row["contact_email"],
            result["email"]["subject"],
            result["email"]["body"],
            thread_id=row["thread_id"],
            in_reply_to=row["initial_message_id"] or row["message_id"],
        )
        mark_nudge_sent(row["id"], sent["id"])
        results.append(
            {
                "id": row["id"],
                "status": "SENT",
                "message_id": sent["id"],
                "evidence_ids": evidence_ids(row),
            }
        )
    return results
