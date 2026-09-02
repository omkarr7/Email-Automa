# Truth, hallucination and email quality architecture

The system now separates:

1. **Evidence** — raw public source snapshots.
2. **Extraction** — optional LLM or deterministic logic identifies candidate facts from evidence.
3. **Validation** — source hierarchy + corroboration determine whether a fact is approved.
4. **Generation** — templates or models may use approved facts only.
5. **Quality gate** — deterministic checks + optional critic model.
6. **Outcome** — PASS, REVISE/regenerate, or REJECT.

## Core rule

An LLM is never treated as the source of truth.

If a model says:

> "The company is expanding its AI team"

the claim is not usable unless a stored source actually supports it.

## Current vacancies

A current vacancy requires a primary company/ATS source and high-confidence extraction.
A generic search result cannot by itself establish a current vacancy.

## Auditability

`data/evidence.db` stores:

- source URL
- retrieval time
- source type
- HTTP status
- content hash
- source snapshot
- extracted facts
- validation status
- evidence references

## Email safety

An email is blocked if:

- mandatory content is missing;
- it is too short/long;
- company/person context is missing;
- placeholders remain;
- a verified vacancy URL is missing;
- genericity is excessive;
- the critic finds unsupported claims;
- quality scores fall below thresholds;
- all model regeneration attempts fail.

The safe default is **do not send**.

## Model routing

Configure providers through environment variables and `config/routing.yml`.
If no providers are configured, the pipeline falls back to deterministic free mode.
The router supports task-specific ordering for:

- research
- generation
- critic

Additional providers can be added as adapters without changing the business logic.
