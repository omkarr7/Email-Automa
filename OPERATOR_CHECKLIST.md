# Operator checklist

Before live sending:

- [ ] Replace profile placeholders.
- [ ] Verify your official Axion job title and only claim responsibilities you actually performed.
- [ ] Verify every public contact and add an email only when legitimately obtained.
- [ ] Replace placeholder job URLs.
- [ ] Run `pytest -q`.
- [ ] Run `python -m src.main --mode prepare`.
- [ ] Read every generated email in `outbox/`.
- [ ] Keep `SEND_ENABLED=false` until satisfied.
- [ ] Test Gmail with one controlled recipient first.
- [ ] Keep the daily cap low initially.
- [ ] Never send a nudge after a reply or opt-out.
- [ ] Remove anyone who asks not to be contacted.

The pipeline is intentionally conservative because an automated system can amplify a small factual mistake very quickly.
