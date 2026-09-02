import re

PLACEHOLDER_PATTERNS = [
    r"REPLACE_", r"\{\{.*?\}\}", r"\{\%.*?\%\}", r"TODO", r"example\.com"
]

def validate_body(body):
    errors = []
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, body, re.I):
            errors.append(f"Unresolved placeholder: {pattern}")
    if len(body) > 5000:
        errors.append("Email is too long")
    if "I couldn't identify" in body and "advertised position" not in body:
        errors.append("Suspicious vacancy wording")
    return errors

def validate_contact(email):
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return ["Invalid or missing email"]
    return []
