import re
from urllib.parse import urlparse
from .models import CompanyCandidate

LEGAL_SUFFIXES = re.compile(r"\b(pvt|private|limited|ltd|llp|inc|incorporated|corp|corporation|technologies|technology|solutions|labs|laboratories)\b\.?", re.I)

def normalize_name(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = LEGAL_SUFFIXES.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_domain(value: str) -> str:
    if not value:
        return ""
    v = value.strip().lower()
    if "://" not in v:
        v = "https://" + v
    try:
        host = urlparse(v).netloc.lower()
        host = host.split("@")[-1].split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""

def normalize_candidate(c: CompanyCandidate) -> CompanyCandidate:
    c.name = re.sub(r"\s+", " ", (c.name or "").strip())
    c.domain = normalize_domain(c.domain or c.website or "")
    if c.website and not c.website.startswith(("http://", "https://")):
        c.website = "https://" + c.website
    return c
