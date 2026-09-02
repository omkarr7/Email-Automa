import re

ROLE_KEYWORDS = {
    "data analyst": ["analytics", "sql", "reporting", "bi", "data"],
    "data scientist": ["machine learning", "statistics", "python", "data science"],
    "data engineer": ["python", "sql", "etl", "pipeline", "data engineering"],
    "analytics engineer": ["sql", "analytics", "dbt", "data"],
    "ml engineer": ["machine learning", "python", "pytorch", "ml"],
    "ai engineer": ["ai", "python", "llm", "machine learning"],
    "data governance": ["governance", "data quality", "metadata", "controls"],
    "product analyst": ["product analytics", "sql", "experimentation", "analytics"],
    "data operations": ["data quality", "operations", "sql", "data"],
}

def normalise(text):
    return set(re.findall(r"[a-z0-9+#.]+", (text or "").lower()))

def score_job(job, profile, company):
    text = " ".join([
        job.get("job_title",""), job.get("description",""),
        company.get("domain",""), company.get("current_signal","")
    ]).lower()

    skills = set()
    for group in profile.get("skills", {}).values():
        skills.update(str(x).lower() for x in group)

    matched = [s for s in skills if s in text]
    score = min(40, len(matched) * 5)

    title = job.get("job_title","").lower()
    role_match = 0
    for role, keys in ROLE_KEYWORDS.items():
        if role in title:
            role_match = 25
            if any(k in text for k in keys):
                role_match += 10
            break

    years = 0
    try: years = float(job.get("years_required") or 0)
    except ValueError: pass
    experience = 20 if years <= 1 else 15 if years <= 2 else 5 if years <= 3 else 0

    city_match = 10 if job.get("location","").lower() in {"bengaluru","mumbai","pune"} else 0

    return min(100, score + role_match + experience + city_match)
