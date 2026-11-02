# BevStats

Shared Supabase dashboard for 22 restaurants. Display units are case equivalents, comparing October 1-29, 2026 against October 1-29, 2025. Duplicate Bud Light detail rows are excluded. Source changes and percentages are preserved exactly, including source rounding differences. Anyone can view without signing in. Only the configured owner may insert or update database rows; owner editing and daily import UI remain pending.

## Database setup

The supplied URL and publishable key are configured in `pitcher-tracker/supabase-public.json`. They are public browser configuration, not database administration credentials. The schema, initial import, and owner assignment have been applied. Local browser checks verified public access to all 22 restaurants from the real database.

Using the Supabase integration or project SQL editor:

1. Run `pitcher-tracker/supabase/schema.sql` once to create tables, public read policies, owner-only insert/update policies, and the dashboard view. Existing objects are not deleted. Owner assignment is protected from browser changes. Browser roles have no sales delete permission.
2. Run `pitcher-tracker/supabase/initial-import.sql` to load the 22 restaurant rows. This atomic import can be reapplied without duplicating report/location rows. Exact source values are also saved in `supabase/first-report.json`.
3. Create and confirm `jeff.eckard@daitaspark.com` in Supabase Auth. Run `pitcher-tracker/supabase/assign-admin.sql` to bind that confirmed Auth user to the sole owner record. Typing the email in the app does not grant permissions.
4. Disable public signups. Allow `http://localhost:8001/` and your deployed site URL in Supabase Auth redirect URLs. Configure email delivery for the admin address and keep the default magic-link email template. The Admin button requests a link for the existing account without creating a new account. The callback verifies the Auth identity and checks database ownership. Authentication tokens are removed from the callback URL and stored in session storage.
5. Verify public reads, denied non-owner writes, successful owner insert/update, and denied ownership changes against the live project. Local mocked browser checks do not verify deployed database policies.

## Local preview

```powershell
cd pitcher-tracker
python build_static.py
python -m http.server 8001 --directory static --bind 127.0.0.1
```

Open http://localhost:8001. The dashboard has no sample-data fallback and ignores old browser-local demo sales. Until the schema/import are applied, it displays the database error. Report totals are read-only in the current dashboard. CSV export, search, filtering, pagination, and pitcher animations remain available. The latest report is selected by current-period end date, load time, then ID.

`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` build environment variables override the checked-in public configuration. Never use a secret or service-role key in browser assets. On Render Static Site use root `pitcher-tracker`, build command `python build_static.py`, and publish directory `static`. The previous echo-only build command does not regenerate configuration.

## Checks and legacy backend

Run `python -m unittest -v` from `pitcher-tracker`. Build/import tests require no third-party packages. Live authentication, email delivery, database import, and row-level security still need verification after connecting the project.

`server.py` and its SQLite tests are legacy backend code. Their sample fixtures are not shipped in the Supabase build. Use the static preview above for the real dashboard.
