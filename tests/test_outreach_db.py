from src.outreach_db import connect, insert_prepared, mark_reply, mark_sent, due_for_nudge
from datetime import datetime, timezone, timedelta

def test_reply_stops_nudge():
    # Unique test values avoid collisions with any existing local DB.
    stamp=datetime.now(timezone.utc).timestamp()
    conn = connect()
    row_id = insert_prepared(
        conn,
        company="TestCo",
        contact_name=f"Jane{stamp}",
        contact_email=f"jane{stamp}@example.com",
        contact_designation="Head of Data",
        subject="Test subject",
        body="Test body for outreach.",
    )
    mark_sent(
        conn,
        row_id,
        f"message-{stamp}",
        thread_id=f"thread-{stamp}",
        sent_at=(datetime.now(timezone.utc)-timedelta(days=6)).isoformat(),
        nudge_after_days=5,
    )
    row = conn.execute("SELECT * FROM outreach WHERE id=?", (row_id,)).fetchone()
    mark_reply(row["id"],"REPLIED_NEUTRAL","reply-1",datetime.now(timezone.utc).isoformat())
    assert not any(r["id"]==row["id"] for r in due_for_nudge())
