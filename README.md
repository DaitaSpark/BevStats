# SEC Championship Ticket Giveaway

Public restaurant-sales dashboard backed by Supabase. Current report: **November 2026 month-to-date, as of November 3**, compared with the **full October 2026 baseline**. Display volumes are Beers, with smaller CE values underneath (Beers / 24). Percentages display as whole numbers. Tiles sort by total Beers or percentage change.

## Current data and daily imports

Run `pitcher-tracker/supabase/import-november-02-2026.sql` in Supabase SQL Editor for the latest supplied report. It loads 22 restaurant entries, excluding Total and Bud Light product rows, and multiplies CE volumes by 24 once before storing them. It preserves location IDs, existing addresses, Auth accounts, editor access, and historical snapshots.

This import explicitly replaces the earlier partial October baselines with the supplied full-month October amounts. Wild Wing's corrected baseline is 62 CE / 1,488 Beers. Future daily imports preserve established October baselines unless a baseline correction is explicitly authorized in their source JSON.

Restaurant-row totals are 592.47 CE / 14,219.28 Beers for October and 62.01 CE / 1,488.24 Beers for November. The printed Total row differs slightly (592.44 and 62.00 CE); individual restaurant values are preserved. Source rounded changes and percentages remain stored. The app computes comparisons against the stored October baseline.

Daily reports use `as_of_date` to select the latest snapshot, independently of source column headings. The current report period is November 1-2, 2026. Reimporting the same as-of date replaces that snapshot's imported totals without duplicating it; other days remain available as history. Each daily source must contain cumulative month-to-date totals, not quantities to add to yesterday. Missing restaurants remain awaiting data; reported zeros are real entries.

Generate a daily SQL file with:

```powershell
cd pitcher-tracker
python supabase/prepare_daily_import.py --source supabase/november-02-2026-report.json --output supabase/import-november-02-2026.sql
```

Report JSON, import SQL, and legacy setup scripts are retained in this repository for reference. Use the dated daily importer for routine updates. Do not use older clean-reload scripts: they replace sales data and are not the daily workflow.

## Viewing and editing

Everyone can view without signing in. Jeff (`jeff.eckard@daitaspark.com`) and Corey (`corey.eckard@eaglerocks.com`) can use Admin with their Supabase Auth email/password to edit current Beers totals, names, and addresses. The October baseline is read-only; comparisons calculate automatically. Save includes edited rows hidden by filters/pages, submits one transaction, and detects conflicting edits.

Existing accounts without a password can use Admin ? Set / reset password. Open the newest recovery email and choose/confirm a password in the app. Allow the app URL in Supabase Authentication ? URL Configuration ? Redirect URLs. Public signups should remain disabled. Do not place passwords or service-role keys in frontend files, SQL, or chat.

## Build and hosting

Public project settings are in `pitcher-tracker/supabase-public.json`. Build environment variables `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` can override them. Only a publishable/legacy anon key may appear in frontend assets.

```powershell
cd pitcher-tracker
python build_static.py
python -m http.server 8001 --directory static --bind 127.0.0.1
```

Local preview: http://localhost:8001/. Render site: https://bevstats.onrender.com/. Render root is `pitcher-tracker`, build command `python build_static.py`, publish directory `static`. Deploy the pending daily-snapshot selection update after running the latest import. Subsequent daily data imports do not require app redeployments.

## Checks

Run `python -m unittest -v` from `pitcher-tracker`. Local browser checks use simulated database responses for daily snapshot selection, totals, CE labels, editing, and recovery. Live imports and sign-in must be verified in the connected project; no real passwords are used in simulated checks.

`server.py` and its SQLite tests are a legacy backend. The production static build uses Supabase and does not seed samples or fall back to browser-local demo sales.

B&W Burgers Buns & Brews was added to the November 2 source with October, November, change and percentage all zero. To add only that row to an already imported report, use `supabase/add-bw-burgers-november-02-2026.sql`; the full dated import also includes it. Totals are unaffected.

## November 3 cumulative update

Run `supabase/import-november-03-2026.sql` for the November 3 month-to-date update. This replaces cumulative values in the day's snapshot, retains previous reports and stable location IDs, and performs no inserts, updates, deletes or schema changes on the October baseline table. Actual zero entries remain zero. The 21 supplied restaurant rows match the prior cumulative values; B&W's explicitly added zero row is retained separately and marked as carried forward in the source JSON. Totals are 62.01 CE / 1,488.24 Beers when summing individual rows, compared with 62.00 CE printed in the report Total.

No app redeploy is required: the published app already selects the latest as-of date. This update does not run the clean-reload scripts or the November 2 baseline correction. Regenerate with `python supabase/prepare_daily_import.py --source supabase/november-03-2026-report.json --output supabase/import-november-03-2026.sql`. Live database execution is pending.

## November 4 cumulative update

`supabase/import-november-04-2026.sql` loads the report confirmed as of November 4. It replaces cumulative totals in that dated snapshot, retains previous reports and stable location IDs, and makes no changes to October's baseline table. The 21 restaurant rows exclude product and Total rows; B&W's explicitly supplied zero entry is retained as a documented carried-forward row. Row totals are 144.68 CE / 3,472.32 Beers, versus the printed Total of 144.67 CE. Original restaurant values and source rounding differences are preserved. No live import has been executed by the assistant. No app deployment is required after running the SQL.

## Hourly live-report sync

See [hourly sync setup](pitcher-tracker/supabase/HOURLY-SYNC.md) for the migration, Edge Function deployment, manual validation, hourly Cron schedule, and dashboard timestamp. The sync function is deployed and hourly polling is active as of November 6, 2026. The dashboard assets include the last-successful-check timestamp.
