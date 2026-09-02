from src.email_quality import deterministic

def test_blocks_short_email():
    assert "too_short" in deterministic("Hi", "Acme", "Rahul")

def test_blocks_missing_company():
    body = "Hello Rahul,\n\n" + ("This is a detailed message. " * 30)
    assert "company_missing" in deterministic(body, "Acme", "Rahul")

def test_blocks_generic_email():
    body = """Hello Rahul,
I am writing to express my interest. I was impressed by your innovative work.
I believe my skills and experience would make me a valuable addition to your team.
I would love to explore opportunities.
""" + ("More context. " * 20)
    assert "generic_language" in deterministic(body, "Acme", "Rahul")


def test_allows_shorter_followup_validation():
    body = (
        "Hello Rahul,\n\n"
        "Following up on my earlier note about opportunities at Acme. "
        "My background across Python, SQL and analytics remains relevant.\n\n"
        "Best regards,\nOmkar"
    )
    assert deterministic(
        body,
        "Acme",
        "Rahul",
        min_length=60,
        max_length=800,
        require_person=False,
    ) == []
