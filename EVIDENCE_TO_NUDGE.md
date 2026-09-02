# Evidence → initial email → reply detection → nudge

The full state flow is now connected.

```text
Source URLs
    ↓
evidence.db
    ↓
candidate facts
    ↓
truth validation
    ↓
APPROVED FACTS + evidence IDs
    ↓
email generation
    ↓
quality gate
    ↓
main send flow / send_outreach.send_and_register()
    ↓
Gmail thread_id + message_id + approved facts stored
    ↓
inbox_monitor
    ↓
NO_REPLY ───────────────→ nudge due
REPLY ──────────────────→ stop
    ↓
nudge_runner
    ↓
retrieve EXACT approved facts from outreach.db
    ↓
generate nudge
    ↓
quality gate
    ↓
send in same Gmail thread
```

## Critical safety properties

1. The nudge does **not** perform new open-ended research.
2. The nudge can only use facts already approved by the truth layer.
3. The exact evidence IDs used for the initial outreach are retained.
4. If no approved facts are stored, the nudge is rejected.
5. If the person replies, the no-reply nudge path stops.
6. Only one automated nudge is allowed.
7. Sending requires `SEND_ENABLED=true`.
8. `DRY_RUN=true` remains the default.

## Initial-send integration

The default `python -m src.main --mode send` flow now stores the same verified
context automatically.

If you are using the lower-level generation helpers directly, keep using:

After your existing generation + critic pipeline returns `PASS`:

```python
from src.send_outreach import send_and_register

record = send_and_register(
    context={
        "company": company_name,
        "recipient": person_name,
        "recipient_email": person_email,
        "designation": designation,
    },
    email=generated_email,
    approved_facts=approved_facts,
    evidence_ids=evidence_ids,
)
```

That is the missing bridge: it stores the exact verified context that the later nudge is allowed to use.
