"""Gmail thread tracking and sending."""
import base64
import os
from mimetypes import guess_type
from pathlib import Path
from email.message import EmailMessage

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
ROOT = Path(__file__).resolve().parents[1]
TOKEN = ROOT / "data" / "gmail_token.json"
CREDS = ROOT / "credentials.json"

def _service():
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS.exists():
                raise RuntimeError("credentials.json is missing. See GMAIL_SETUP.md")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)

def resolve_resume_pdf_path():
    configured = os.getenv("RESUME_PDF_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"RESUME_PDF_PATH does not exist: {path}")
        return path

    default_path = ROOT / "data" / "resume.pdf"
    return default_path if default_path.exists() else None

def _attach_file(message, path):
    path = Path(path)
    mime_type, _ = guess_type(str(path))
    maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
    message.add_attachment(
        path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=path.name,
    )

def send_message(to, subject, body, thread_id=None, in_reply_to=None, attachment_paths=None):
    service = _service()
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)

    for attachment_path in attachment_paths or []:
        _attach_file(msg, attachment_path)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    return service.users().messages().send(userId="me", body=payload).execute()


def send_email(to, subject, body, thread_id=None, in_reply_to=None):
    return send_message(to, subject, body, thread_id=thread_id, in_reply_to=in_reply_to)

def _headers(message):
    return {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

def _body(message):
    import base64
    payload = message.get("payload", {})
    chunks = []
    if payload.get("body", {}).get("data"):
        chunks.append(payload["body"]["data"])
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            chunks.append(part["body"]["data"])
    if not chunks:
        return ""
    try:
        return base64.urlsafe_b64decode(chunks[0] + "==").decode("utf-8", "ignore")
    except Exception:
        return ""

def thread_messages(thread_id):
    return _service().users().threads().get(userId="me", id=thread_id, format="full").execute().get("messages", [])

def classify_reply(message, my_email):
    h = _headers(message)
    sender = h.get("from", "")
    if my_email.lower() in sender.lower():
        return {"kind": "SELF", "confidence": 1.0}
    text = (h.get("subject", "") + "\n" + _body(message)).lower()

    if any(x in text for x in ["out of office", "automatic reply", "auto-reply", "autoreply", "away from the office"]):
        return {"kind": "AUTO_REPLY", "confidence": .95}
    if any(x in text for x in ["not hiring", "no openings", "no vacancy", "position has been filled", "do not contact"]):
        return {"kind": "REPLIED_NEGATIVE", "confidence": .9}
    if any(x in text for x in ["send your cv", "send your resume", "let's talk", "schedule a call", "interview", "happy to connect", "interested"]):
        return {"kind": "REPLIED_POSITIVE", "confidence": .8}
    return {"kind": "REPLIED_NEUTRAL", "confidence": .7}

def check_thread(thread_id, my_email):
    external = []
    for m in thread_messages(thread_id):
        result = classify_reply(m, my_email)
        if result["kind"] != "SELF":
            h = _headers(m)
            external.append({
                "message_id": m.get("id"),
                "received_at": h.get("date"),
                "subject": h.get("subject", ""),
                **result
            })
    if not external:
        return {"reply": False, "kind": "NO_REPLY"}
    return {"reply": True, **external[-1]}
