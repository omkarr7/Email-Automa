from src.discovery.models import CompanyCandidate
from src.discovery.normalizer import normalize_candidate, normalize_name
from src.discovery.deduplicator import is_duplicate

def test_domain_dedup():
    c=normalize_candidate(CompanyCandidate(name="Example Technologies",domain="https://www.example.com"))
    existing=[{"domain":"example.com","website":"https://example.com","canonical_name":"Example Technologies","name":"Example Technologies"}]
    assert is_duplicate(c,existing)[0]

def test_name_normalization():
    assert normalize_name("Example Technologies Pvt. Ltd.") == "example"
