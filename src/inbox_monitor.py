import os
from .gmail import check_thread
from .outreach_db import connect, mark_reply, mark_checked

def monitor():
    my_email = os.environ["GMAIL_ADDRESS"]
    c = connect()
    rows = c.execute("""SELECT * FROM outreach
        WHERE lower(status) IN ('sent','nudged') AND thread_id IS NOT NULL
        AND reply_status='NO_REPLY'""").fetchall()
    changes = []
    for row in rows:
        result = check_thread(row["thread_id"], my_email)
        if not result["reply"]:
            mark_checked(row["id"])
            continue
        mark_reply(row["id"], result["kind"], result.get("message_id"), result.get("received_at"))
        changes.append({"id":row["id"],"company":row["company"],"person":row["contact_name"],"status":result["kind"]})
    return changes

if __name__ == "__main__":
    print(monitor())
