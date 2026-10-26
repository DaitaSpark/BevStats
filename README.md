# BevStats

A Bud Light sample sales dashboard with animated pitcher cards, six locations per desktop row, search, filters, pagination, editable tables, and CSV export.

## Render Static Site: recommended for the current demo

This version serves static files with no Python process or sleeping web service. The pitcher graphics, animations, and dashboard UI use the same source as the Python version.

Create **New > Static Site** in Render and connect `DaitaSpark/BevStats`:

| Setting | Value |
| --- | --- |
| Branch | `main` |
| Root directory | `pitcher-tracker` |
| Build command | `echo "BevStats static site ready"` |
| Publish directory | `static` |

There is **no start command**, disk, database, or required environment variable. Do not copy login-password environment variables into static frontend assets. The publish directory is prebuilt and committed, so Render does not need Python or any packages to build it. Use the new Static Site URL; the old Web Service URL still has its wake-up behavior. If using a custom domain, move it to the Static Site when ready.

### What is saved

- A new browser starts with all 18 sample locations. The demo profile needs only a username and a password of at least four characters. The header shows the username; existing profiles and passwords continue to work.
- Sales edits and one demo profile are saved in that browser's local storage and survive page reloads and redeploys at the same origin.
- Signing out clears the tab's session, not the saved sales. Sessions expire after eight hours.
- Data and profiles are **not shared across devices, browsers, domains, or colleagues**. Everyone begins with their own sample data. Profiles on different devices can have different names and passwords.
- This is a public demo. The sign-in modal demonstrates the flow; browser-only sign-in does **not** protect private data. Use a demo password. Demo passwords are salted and hashed in the browser rather than stored as plaintext, but users can bypass the UI locally.
- Clearing browser/site storage removes local sales and profiles. CSV export downloads a copy; CSV import is not implemented. **Restore samples** replaces local sales with the original 18 samples.

Supabase integration is deferred. It can later provide real authentication and durable shared sales while keeping the frontend statically hosted.

## Local static preview

Requires Python only to serve files locally, not on Render:

```sh
cd pitcher-tracker
python build_static.py
python -m http.server 8001 --directory static --bind 127.0.0.1
```

Open http://localhost:8001. Use localhost or HTTPS for browser password hashing. After any dashboard, adapter, favicon, or sample-data change, run `python build_static.py` and commit the regenerated files under `static/`.

## Optional Python backend

The original server remains available for local development or later backend work:

```sh
cd pitcher-tracker
python server.py
```

Open http://localhost:8000. That mode uses server-side sign-in and SQLite, not the browser-only adapter. Its existing sales and accounts are untouched. See [the app guide](pitcher-tracker/README.md) for backend accounts and the previous Web Service deployment options.

## Checks

```sh
cd pitcher-tracker
python -m unittest -v
```
