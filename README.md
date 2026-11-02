# BevStats

Shared Supabase dashboard for 22 restaurants. Display units are Beers (24 per source case equivalent), comparing October 1-29, 2026 against October 1-29, 2025. Duplicate Bud Light detail rows are excluded. Source changes and percentages are preserved exactly, including source rounding differences. Anyone can view without signing in. Only Jeff and Corey can edit the table after email/password sign-in; daily import UI remains pending.

## Database setup and editor access

The report tables, imported data, and Beers conversion have already been applied. For the restored editor, run `pitcher-tracker/supabase/enable-table-editing.sql` in the Supabase SQL Editor. It replaces single-owner write policies with verified-account access for exactly `jeff.eckard@daitaspark.com` and `corey.eckard@eaglerocks.com`, adds a permission-check RPC and an atomic save RPC, and preserves public viewing. This migration can be reapplied. It does not modify report values or create Auth accounts.

Create/confirm both email accounts under Supabase Authentication ? Users and assign each their own password. Existing confirmed accounts with passwords can be reused. Do not put passwords in SQL, frontend config, source control, or chat. The app does not create accounts. Admin sign-in now uses email and password directly, with no email link or redirect needed for normal sign-in. Public signups should remain disabled.

Click **Admin**, enter one of the two account emails and its password, then edit the table. Subsequent edits use **Edit table** or **Update sales**. Editable fields are location name, address, prior-year Beers, current Beers, and the source comparison percentage. Changing either total recalculates percentage where a prior-year baseline exists; you can override the percentage to match a report. Blank numeric fields remain null. Source rounded count differences are preserved when totals are unchanged, and recalculated when totals change. Read-only tiles/table still show only current Beers and whole-number comparison percentages. CSV retains original precision.

**Save changes** submits only changed rows, including those hidden by filters/pages, in one database transaction. Stored original values detect concurrent edits; conflicts roll back the whole save and keep the browser draft. Cancel reloads the saved report. Adding/deleting locations and daily report imports are outside this editor update.

For a new database, use `supabase/schema.sql`, `supabase/initial-import.sql`, and `supabase/enable-table-editing.sql` in order, then provision the two Auth accounts. Do not rerun schema.sql on the existing project. The older `assign-admin.sql` is retained for legacy setup and is not needed for the two-editor access rules.

## Local preview

```powershell
cd pitcher-tracker
python build_static.py
python -m http.server 8001 --directory static --bind 127.0.0.1
```

Open http://localhost:8001. The dashboard has no sample-data fallback and ignores old browser-local demo sales. Until the schema/import are applied, it displays the database error. Reports are public, with table editing available to the two authorized accounts after applying enable-table-editing.sql. CSV export, search, filtering, pagination, and pitcher animations remain available. The latest report is selected by current-period end date, load time, then ID.

`SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` build environment variables override the checked-in public configuration. Never use a secret or service-role key in browser assets. On Render Static Site use root `pitcher-tracker`, build command `python build_static.py`, and publish directory `static`. The previous echo-only build command does not regenerate configuration.

## Checks and legacy backend

Run `python -m unittest -v` from `pitcher-tracker`. Build/import tests require no third-party packages. Live authentication, email delivery, database import, and row-level security still need verification after connecting the project.

`server.py` and its SQLite tests are legacy backend code. Their sample fixtures are not shipped in the Supabase build. Use the static preview above for the real dashboard.

## Converting the existing database to Beers

Run `pitcher-tracker/supabase/convert-to-beers.sql` in the Supabase SQL Editor before deploying the new dashboard. It transactionally renames the stored volume columns to `prior_beers`, `current_beers`, and `reported_change_beers`, multiplies them by 24, and leaves percentages and beer prices unchanged. A column-existence guard prevents repeat conversion; the whole migration rolls back on error. Existing row IDs, permissions and owner assignment are preserved. Do not rerun schema.sql on an existing database.

The dashboard reads the new beer values directly; it does not multiply browser values. The view retains old case-equivalent API fields for the previous app during rollout. The regenerated initial import also writes beers, so reimporting the original source does not change units back. Keep first-report.json as the original source in case equivalents. Fractional results are retained to two decimal places: no rounding to whole beers was requested.

For the initial 22-location report, the conversion verification query should return current beers **12,070.32** and prior beers **16,037.28**. Wild Wing current volume becomes **1,488.00 Beers**, with reported change **165.36 Beers** and unchanged **12.50%**. The migration has been applied and all 22 live rows verified against the source: all three volume fields equal the originals multiplied by 24, with percentages unchanged.

## First password / password recovery

An existing Auth account without a password (Jeff's initial account) does not need to be deleted. In the local app open Admin, enter the existing email, and click Set / reset password. Supabase sends a recovery link. Open the newest link, choose and confirm a password of at least 12 characters in the app, and save. Successful setup opens the editable table. Routine sign-in then uses email/password without links. The request does not create new users.

Allow `http://localhost:8001/` in Supabase Authentication ? URL Configuration ? Redirect URLs when testing locally. For production allow `https://bevstats.onrender.com/` and deploy this app version before requesting recovery there. Recovery redirects to the same app origin/path where requested. Keep the default recovery email template (ConfirmationURL). Passwords are submitted directly to Supabase Auth; they are not included in SQL or browser sales storage. Existing Auth confirmation and the two-editor database permission check are still required.

Opening an expired or already used recovery link will show an error; request a new link. The app removes callback tokens from the URL, preserves recovery mode across session reload/refresh until setup completes, and blocks sales saves until the new password is set. Normal sign-in and public viewing continue to work. Browser checks use simulated Auth responses and do not send mail or change real passwords; real email delivery and account password setup require the user's own link.
