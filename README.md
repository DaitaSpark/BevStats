# BevStats

A Bud Light delivered-sales tracker with animated pitcher cards, location rankings, search and filters, CSV export, and password-protected team access.

## Run locally

Requires Python 3.10+; no external packages.

```sh
cd pitcher-tracker
python server.py
```

Open http://localhost:8000 and create the first account in the login modal. New databases include 18 sample locations. Sales and accounts are stored in SQLite and are excluded from Git.

## Deploy on Render

Create a **Python 3 Web Service** connected to this repository's `main` branch:

| Setting | Value |
| --- | --- |
| Root directory | `pitcher-tracker` |
| Build command | `python -m compileall -q server.py` |
| Start command | `python server.py` |
| Health check path | `/` |
| Environment: `HOST` | `0.0.0.0` |
| Environment: `BEVSTATS_DEMO_MODE` | `1` |
| Environment: `BEVSTATS_LOGIN_USERNAME` | Your chosen username |
| Environment: `BEVSTATS_LOGIN_PASSWORD` | Your chosen password (12?256 characters) |
| Environment: `BEVSTATS_LOGIN_NAME` | Your display name (optional) |
| Instance type | Free |

**No disk required for the demo.** Remove `BEVTRACKER_DB` if previously set to `/var/data/sales.sqlite3`. Render provides `PORT`. Add the login password as a secret environment value in Render; never put it in Git. Demo mode requires credentials and disables the public first-account setup by provisioning that account at startup.

Demo mode uses a temporary SQLite file. All 18 samples and the configured login return after Render discards the filesystem, but manual edits and browser-created accounts/sessions may be lost on sleep, restart, or redeploy. All visitors share the current server's temporary data. CSV export lets you download a copy; CSV import is not implemented. This mode is for sample-data evaluation.

For durable shared sales and accounts later, use an external database or a paid persistent disk. To use the existing disk option, remove `BEVSTATS_DEMO_MODE`, mount `/var/data`, and set `BEVTRACKER_DB=/var/data/sales.sqlite3`. Local development remains unchanged unless demo mode is explicitly enabled.

## Checks

```sh
cd pitcher-tracker
python -m unittest -v
```

See [the app guide](pitcher-tracker/README.md) for account provisioning, storage, and current limitations.
