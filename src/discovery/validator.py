import re
from urllib.parse import urlparse

def validate_candidate(candidate):
    """
    Conservative validation before insertion.
    The discovery layer does not claim a company is hiring merely because it
    appeared in search results.
    """
    errors=[]
    if not candidate.name or len(candidate.name.strip()) < 2:
        errors.append("missing_name")

    domain=candidate.domain or ""
    if domain:
        if "." not in domain or " " in domain:
            errors.append("invalid_domain")

    if candidate.website:
        try:
            parsed=urlparse(candidate.website if "://" in candidate.website else "https://"+candidate.website)
            if not parsed.netloc:
                errors.append("invalid_website")
        except Exception:
            errors.append("invalid_website")

    return (len(errors)==0, errors)
