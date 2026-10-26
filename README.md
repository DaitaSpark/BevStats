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
| Environment: `BEVTRACKER_DB` | `/var/data/sales.sqlite3` |
| Persistent disk mount | `/var/data` |

Use a paid instance with a persistent disk to retain accounts and sales across deployments. Render provides `PORT`. A new hosted database starts with sample data and needs its own first account; local accounts are not pushed to GitHub. Provision the first account before sharing the site.

## Checks

```sh
cd pitcher-tracker
python -m unittest -v
```

See [the app guide](pitcher-tracker/README.md) for account provisioning, storage, and current limitations.
