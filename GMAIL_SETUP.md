# Gmail reply tracking + nudge

1. Enable Gmail API in Google Cloud.
2. Create an OAuth Desktop App credential.
3. Save the downloaded JSON as `credentials.json` in the project root.
4. Install requirements.
5. Set:

```env
GMAIL_ADDRESS=you@example.com
NUDGE_AFTER_DAYS=5
DRY_RUN=true
SEND_ENABLED=false
RESUME_PDF_PATH=data/resume.pdf
```

On first Gmail use, the script opens a browser for OAuth and saves `data/gmail_token.json`.
If you want the resume attached to outgoing initial emails, place the PDF at
`data/resume.pdf` or point `RESUME_PDF_PATH` at another local file.

## Reply logic

Each sent outreach is registered with its Gmail `thread_id` and initial `message_id`.
The monitor checks that exact thread.

External replies become:
- `REPLIED_POSITIVE`
- `REPLIED_NEUTRAL`
- `REPLIED_NEGATIVE`
- `AUTO_REPLY`

Any external reply stops the normal no-reply nudge path.

## Nudge logic

Default: one nudge after 5 days with no external reply.

Before sending, the nudge passes the same deterministic and critic quality gates.
If generation or quality checks fail, it is rejected rather than sent.

## Cron

```cron
0 9 * * * cd /path/to/project && .venv/bin/python -m src.main --mode monitor
0 10 * * * cd /path/to/project && .venv/bin/python -m src.main --mode nudge
```

Keep dry-run enabled until you have inspected several cycles.

## GitHub Actions resume attachment

If you run the send workflow in GitHub Actions, add a secret named
`RESUME_PDF_BASE64` containing your PDF encoded as base64. The workflow can
materialize it into `data/resume.pdf` before sending.

## Private overrides

Keep your real values out of git by placing them in:

- `.env.local`
- `config/profile.local.yml`
- `data/contacts.local.csv`

The app will prefer those files when present.


## Evidence continuity

The main send flow now stores:

- Gmail thread ID
- initial message ID
- approved facts
- evidence IDs
- original email

The nudge runner reads the approved facts from this record. It does not invent
new company facts and does not run fresh unrestricted research while generating
the follow-up.
