from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class CompanyCandidate:
    name: str
    domain: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    source: str = "unknown"
    source_url: Optional[str] = None
    discovery_reason: Optional[str] = None

    def as_dict(self):
        return asdict(self)
