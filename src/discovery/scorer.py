def score_company(candidate, signals=None):
    """
    Transparent heuristic score. Signals may be supplied by source adapters.
    No LLM is required to assign the base score.
    """
    signals = signals or {}
    score = 0

    if signals.get("hiring"):
        score += 25
    if signals.get("relevant_vacancy"):
        score += 20
    if signals.get("recent_funding"):
        score += 15
    if (candidate.city or "").lower() in {"bengaluru", "bangalore", "mumbai", "pune"}:
        score += 15
    if signals.get("growth_stage"):
        score += 10
    if signals.get("data_heavy"):
        score += 10
    if signals.get("engineering_expansion"):
        score += 5

    return min(score, 100)

def priority(score):
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    return "LOW"
