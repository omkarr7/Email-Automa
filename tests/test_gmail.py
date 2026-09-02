import base64
from email import message_from_bytes

from src import gmail


class _Sent:
    def execute(self):
        return {"id": "msg-1", "threadId": "thread-1"}


class _Messages:
    def __init__(self, captured):
        self.captured = captured

    def send(self, userId, body):
        self.captured["userId"] = userId
        self.captured["body"] = body
        return _Sent()


class _Users:
    def __init__(self, captured):
        self.captured = captured

    def messages(self):
        return _Messages(self.captured)


class _Service:
    def __init__(self, captured):
        self.captured = captured

    def users(self):
        return _Users(self.captured)


def _decode_raw(raw):
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def test_send_message_adds_pdf_attachment(tmp_path, monkeypatch):
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%test resume pdf\n")

    captured = {}
    monkeypatch.setattr(gmail, "_service", lambda: _Service(captured))

    result = gmail.send_message(
        "recipient@example.com",
        "Subject line",
        "Hello there",
        attachment_paths=[pdf],
    )

    assert result["id"] == "msg-1"
    raw = captured["body"]["raw"]
    parsed = message_from_bytes(_decode_raw(raw))
    filenames = [part.get_filename() for part in parsed.walk() if part.get_filename()]

    assert parsed.is_multipart()
    assert "resume.pdf" in filenames
