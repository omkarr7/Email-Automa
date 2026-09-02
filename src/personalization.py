def build_personalisation(company, job, profile):
    domain = (company.get("domain") or "").lower()
    areas = profile.get("experience", {}).get("axion", {}).get("areas", [])
    candidate_fit = ", ".join(areas[:4])

    if "governance" in domain or "data" in domain and "governance" in company.get("current_signal","").lower():
        reason = "your focus on data and the way you build products around trustworthy, well-managed data particularly caught my attention."
    elif "climate" in domain or "environment" in domain or "geospatial" in domain:
        reason = "the combination of data, analytics and real-world environmental applications particularly caught my attention."
    elif "health" in domain:
        reason = "the use of data and AI in a real-world healthcare setting particularly caught my attention."
    elif "fintech" in domain:
        reason = "the combination of data, technology and financial products particularly caught my attention."
    elif "ai" in domain or "generative" in domain:
        reason = "the practical application of AI and data in your product particularly caught my attention."
    else:
        reason = "the data and technology work your team is doing particularly caught my attention."

    return {
        "reason": reason,
        "relevant_area": job.get("description") or "data and analytics",
        "candidate_fit": candidate_fit,
        "confidence": 0.82
    }
