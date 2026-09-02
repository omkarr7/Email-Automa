"""
Provider-neutral discovery adapter.

Set up your chosen search provider in this function. The rest of the discovery
pipeline is provider-independent.

Expected return:
[
  CompanyCandidate(name=..., domain=..., website=..., source=..., source_url=...)
]
"""
from .discovery.models import CompanyCandidate

def search_company_candidates(query):
    # Safe placeholder. Configure a search API / approved source adapter here.
    # Returning [] prevents accidental scraping of sites that may prohibit it.
    return []
