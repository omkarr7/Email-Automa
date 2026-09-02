from difflib import SequenceMatcher
from .normalizer import normalize_name, normalize_domain

def similarity(a, b):
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()

def duplicate_key(candidate):
    domain = normalize_domain(candidate.domain or candidate.website or "")
    name = normalize_name(candidate.name)
    return domain or name

def is_duplicate(candidate, existing_rows, threshold=0.92):
    c_domain = normalize_domain(candidate.domain or candidate.website or "")
    c_name = normalize_name(candidate.name)

    for row in existing_rows:
        r_domain = normalize_domain(row["domain"] or row["website"] or "")
        r_name = normalize_name(row["canonical_name"] or row["name"] or "")

        if c_domain and r_domain and c_domain == r_domain:
            return True, "domain_match"

        if c_name and r_name and c_name == r_name:
            return True, "canonical_name_match"

        if c_name and r_name and similarity(c_name, r_name) >= threshold:
            return True, "fuzzy_name_match"

    return False, None
