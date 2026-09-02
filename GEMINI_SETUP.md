# Gemini integration

This version uses the Gemini API for two things:

1. **Vacancy classification**
   - CURRENT: the supplied job evidence supports that the role is currently advertised.
   - NOT_CURRENT: supplied evidence does not support a current vacancy.
   - UNKNOWN: insufficient evidence.
   - Only CURRENT jobs can enter the vacancy email template.

2. **Structured personalisation**
   Gemini returns JSON fields:
   - `company_reason`
   - `candidate_fit`
   - `relevant_area`
   - `confidence`
   - `evidence_notes`
   - `safe_to_contact`

It does NOT generate the entire email. Jinja remains responsible for the final email structure.

## Setup

```bash
pip install -r requirements.txt
```

Set:

```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

## Important

Gemini can only reason from the data you provide it in this starter implementation. The pipeline intentionally does not ask it to invent current vacancies.

To make vacancy detection genuinely useful, the next step is to add a compliant discovery layer that collects:

- careers page URL
- job title
- job URL
- posted/updated date when available
- location
- job description
- source
- last checked timestamp

Then Gemini can classify that evidence before deciding which template to use.

For a stronger production setup, persist the source evidence and have the model return the exact evidence item(s) supporting each claim.
