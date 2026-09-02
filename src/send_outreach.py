"""
Safe initial-email sender.

Call this only after generation + quality validation have produced PASS.
It stores the exact approved facts/evidence alongside Gmail IDs so the future
nudge can use the same verified context.
"""
import os
from .gmail import resolve_resume_pdf_path, send_message
from .outreach_db import register_sent

def send_and_register(context, email, approved_facts, evidence_ids):
    if os.getenv("SEND_ENABLED","false").lower() != "true":
        raise RuntimeError("SEND_ENABLED is not true; refusing to send.")

    attachment_paths = []
    resume_path = resolve_resume_pdf_path()
    if resume_path:
        attachment_paths = [resume_path]
    else:
        raise RuntimeError("No resume PDF found. Put it at data/resume.pdf or set RESUME_PDF_PATH.")

    sent = send_message(
        context["recipient_email"],
        email["subject"],
        email["body"],
        attachment_paths=attachment_paths,
    )

    return register_sent(
        company=context["company"],
        name=context["recipient"],
        email=context["recipient_email"],
        designation=context.get("designation",""),
        thread_id=sent.get("threadId"),
        message_id=sent.get("id"),
        nudge_after_days=int(os.getenv("NUDGE_AFTER_DAYS","5")),
        approved_facts=approved_facts,
        evidence_ids=evidence_ids,
        original_email=email
    )
