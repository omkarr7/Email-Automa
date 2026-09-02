from src.validators import validate_body, validate_contact

def test_invalid_email():
    assert validate_contact("bad") 

def test_placeholder_blocked():
    assert validate_body("Hello REPLACE_ME") 
