from src.outreach_db import connect, register_sent, approved_facts, evidence_ids, original_email

def test_verified_context_is_persisted():
    row = register_sent(
        "ExampleCo", "Alex", "alex@example.com", "Head of Data",
        "thread-evidence", "msg-evidence",
        approved_facts=[{"fact_type":"official_product","fact_text":"ExampleCo publishes X","status":"VERIFIED"}],
        evidence_ids=[101, 102],
        original_email={"subject":"Data role","body":"Hello Alex"}
    )
    assert approved_facts(row)[0]["status"] == "VERIFIED"
    assert evidence_ids(row) == [101, 102]
    assert original_email(row)["subject"] == "Data role"
