# Gmail API setup

1. Create a Google Cloud project.
2. Enable Gmail API.
3. Configure OAuth consent.
4. Create an OAuth Desktop application.
5. Download the OAuth client JSON.
6. Run your own local OAuth bootstrap script or adapt `src/gmail.py` to generate a token.
7. Store the resulting authorised token JSON in `GMAIL_TOKEN_JSON`.

For GitHub Actions, put the token JSON in a GitHub Actions secret named `GMAIL_TOKEN_JSON`.

Start with a dedicated mailbox or alias and keep `SEND_ENABLED=false` while testing.

Do not commit OAuth credentials, refresh tokens, or `.env`.
