# Weekly company discovery

The project now has an incremental discovery layer.

## What happens each week

1. Search configured discovery sources.
2. Normalize company names/domains.
3. Validate the minimum identity fields.
4. Deduplicate against the existing company database.
5. Insert only genuinely new companies.
6. Record the source URL and discovery timestamp.
7. Assign a transparent priority score.
8. Leave the company in `DISCOVERED` status for the research/contact pipeline.

## Deduplication

Priority is:

1. exact normalized domain
2. exact normalized company name
3. fuzzy normalized name match

This is intentionally conservative. A fuzzy match is treated as a duplicate rather
than risking duplicate outreach.

## Important: discovery ≠ hiring

A company being discovered does NOT mean it has an open job.

Hiring/vacancy claims still have to go through the evidence + truth validation layer.

## Current provider boundary

`src/web_search_adapter.py` is deliberately provider-neutral. Configure your chosen
search provider there. The rest of the pipeline does not depend on a specific search
vendor.

This avoids baking a potentially brittle scraper into the core system.

## GitHub Actions

`.github/workflows/weekly-discovery.yml` runs every Monday at 02:00 UTC and can also
be started manually.

It commits the updated SQLite database back to the repository.

For higher-scale production use, replace the repository SQLite persistence with
PostgreSQL or another managed database.
