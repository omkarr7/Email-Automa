# Job Outreach Automation

A cautious, resumable job-opportunity outreach pipeline for India (Bengaluru, Mumbai, Pune).
It now runs in a free-by-default mode: no paid APIs are required for the core
prepare, send, monitor and nudge workflow.

## What it does

1. Loads your target companies and candidate profile.
2. Reads local jobs/evidence CSVs and public careers pages.
3. Applies a truth gate before any vacancy claim is used.
4. Scores company/job fit deterministically.
5. Renders personalised emails with Jinja.
6. Runs safety checks and duplicate/reply checks.
7. Defaults to **DRY RUN**: generated emails are saved to `outbox/` and nothing is sent.
8. Tracks outreach in SQLite.
9. Can send through Gmail API after you explicitly enable live sending.
10. Can monitor replies and generate one follow-up after a configurable delay.

## Important design choice

This repository does NOT scrape LinkedIn or invent contact details. Add public/legitimate contact information to `data/contacts.csv`, or connect a compliant discovery provider in `src/discovery.py`.

It also does not let an LLM freely invent company facts. If you add an LLM provider later, it is optional and used only for structured extraction/personalisation on top of the deterministic truth gate.

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python -m src.main --mode init
python -m src.discovery
python -m src.main --mode prepare
```

Then inspect `outbox/`.

### Gemini

Optional only. Set `GEMINI_API_KEY` in `.env` if you want richer extraction or review. See `GEMINI_SETUP.md`. Gemini is deliberately constrained to structured JSON and supplied evidence; it does not freely write your emails.

### Populate your profile

Edit:

- `config/profile.yml`
- `config/profile.local.yml` for private values you do not want in git
- `config/settings.yml`
- `data/companies.csv`
- `data/contacts.csv`
- `data/contacts.local.csv` for private contacts you do not want in git
- `data/jobs.csv`

The app automatically prefers `.local` overrides when they exist, so you can keep
your real profile, contact list, and environment variables out of the public repo.

To attach your resume to outgoing initial emails, place the PDF at `data/resume.pdf`
or set `RESUME_PDF_PATH` in `.env` to another file path. Follow-up emails are still
text-only.

The supplied companies CSV contains the Bengaluru/Mumbai/Pune target list created for this project. Verify each company/contact before sending.
The `jobs.csv` file is the simplest fully free way to verify a vacancy: if a row is active and the URL is real, the pipeline can use it without any external model.

### Run tests

```bash
pytest -q
```

### Dry-run outreach

```bash
python -m src.main --mode prepare
```

### Send

Do not enable this until you have reviewed generated emails.

```bash
SEND_ENABLED=true python -m src.main --mode send
```

For Gmail, set up OAuth credentials as described in `config/gmail_setup.md`.
If you want the resume attached, make sure the PDF exists at `data/resume.pdf`
or configure `RESUME_PDF_PATH`.

### Monitor replies

```bash
python -m src.main --mode monitor
```

### Run follow-ups

```bash
python -m src.main --mode nudge
```

## GitHub Actions

The workflows are intentionally conservative. Scheduled jobs run in `Asia/Kolkata`.

Secrets:

- `GMAIL_CREDENTIALS_JSON` — OAuth client JSON if using Gmail.
- `GMAIL_TOKEN_JSON` — generated token JSON for a pre-authorised mailbox.
- `SEND_ENABLED` — keep `false` until you explicitly want live sending.

For GitHub Actions, SQLite is not a durable database across runners. The workflow therefore commits the SQLite state only if you explicitly enable that behaviour. For production, move state to Postgres/Supabase or another persistent DB.

## Anti-spam / safety defaults

- No duplicate outreach to the same email.
- No nudge after a reply.
- One nudge maximum per contact/thread.
- Minimum 6-day follow-up delay.
- Daily send cap.
- Low-confidence personalisation is blocked.
- Senior roles are penalised rather than falsely represented as matches.
- `DRY_RUN=true` by default.


## Production-grade truth and quality layer

The project now separates source evidence from LLM interpretation. See:

- `TRUTH_AND_QUALITY.md`
- `DISCOVERY_SETUP.md`
- `config/routing.yml`

Run:

```bash
python -m src.discovery
python -m src.main --mode prepare
```

`data/evidence.db` stores source snapshots and provides an audit trail.

No email is eligible for sending merely because an LLM generated it.
The default pipeline still works with no model key at all by using manual jobs,
public evidence, and deterministic scoring/quality gates.
