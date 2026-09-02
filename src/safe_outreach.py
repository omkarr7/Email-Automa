from .generation import generate
from .email_quality import deterministic, critique, passes
from .router import Router

def generate_safe(context, approved_facts, profile, thresholds, max_attempts=3):
    router = Router()
    attempts = []
    last = None

    for attempt in range(1, max_attempts + 1):
        email = generate(context, approved_facts, router)
        body = email.get("body","")
        vacancy_url = next((f.get("value") for f in approved_facts if f.get("fact_type") == "current_vacancy_url"), None)
        if not vacancy_url:
            vacancy = next((f.get("value") for f in approved_facts if f.get("fact_type") == "current_vacancy"), None)
            if isinstance(vacancy, dict):
                vacancy_url = vacancy.get("job_url")
        errors = deterministic(
            body,
            context["company"]["company"],
            context["recipient"],
            vacancy_url
        )
        if errors:
            attempts.append({"attempt": attempt, "stage": "deterministic", "errors": errors})
            continue

        review = critique(
            body, context["company"]["company"], context["recipient"],
            approved_facts, profile, router
        )
        last = review
        attempts.append({"attempt": attempt, "stage": "critic", "review": review})

        if passes(review, thresholds):
            return {"status":"PASS", "email":email, "review":review, "attempts":attempts}

    return {
        "status":"REJECT",
        "email":None,
        "review":last,
        "attempts":attempts
    }
