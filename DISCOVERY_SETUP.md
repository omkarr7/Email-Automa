# Public vacancy discovery layer

The pipeline is now:

**Company list → public web discovery → evidence store → truth gate → prepare/send/monitor/nudge**

## Google Custom Search

Create a Google Programmable Search Engine and enable the Custom Search JSON API.

Put these in `.env`:

```env
GOOGLE_CSE_API_KEY=...
GOOGLE_CSE_ID=...
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

Then run:

```bash
python -m src.discovery
```

It creates:

```text
data/discovered_evidence.csv
```

Each record contains:

- company
- source URL
- source title
- source type
- extracted public text
- checked timestamp

## Free mode

Google CSE and Gemini are optional.

If you do not configure them, the discovery step still works in a fully free mode:

- fetch `careers_url` when present;
- fall back to `company_url`;
- try likely public careers paths such as `/careers` and `/jobs`;
- follow public job links found on those pages;
- save evidence to `data/discovered_evidence.csv` and `data/evidence.db`.

That gives you a no-paid-API path as long as your company/contact/job data is curated locally.

## Then classify and prepare

```bash
python -m src.main --mode prepare
```

If Gemini is configured, it receives the collected evidence and returns:

- CURRENT / NOT_CURRENT / UNKNOWN
- job title
- job URL
- location
- job summary
- company personalisation
- candidate fit
- evidence URLs
- evidence notes
- confidence

Without Gemini, the pipeline falls back to deterministic evidence handling and still
requires truth-backed vacancy facts before a vacancy email is rendered.

### Important safeguard

A job is included in the vacancy email only when:

1. the truth layer has approved a current vacancy or `jobs.csv` contains a manually verified active job;
2. a job title exists;
3. a job URL exists;
4. confidence passes the configured threshold.

Otherwise the pipeline uses the no-current-vacancy template.

## What this does NOT do

It does not:

- bypass login walls;
- solve CAPTCHAs;
- scrape LinkedIn behind access controls;
- pretend a stale search result is a live vacancy;
- invent hiring activity;
- send automatically without your existing sending controls.

For production, add a dedicated jobs API / ATS feeds where available. Those are usually more reliable than generic web search.

If you want to keep API keys out of the public repo, put them in `.env.local`
instead of `.env`. The app loads `.env.local` automatically when present.
