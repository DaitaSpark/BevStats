# BevStats

Current dataset: 16 restaurants, October 1-7, 2026 baseline and November 1-7, 2026 actuals. The dashboard reads stored baseline comparisons, shows Beers with smaller CE values (Beers / 24), and follows the source report's +100% convention for positive sales against a zero baseline. Baseline dates come from the database. Older setup sections below describe prior datasets and should not be used to reload this report.

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

## Fixed October 2026 comparison and CE display

Run `pitcher-tracker/supabase/set-october-2026-baseline.sql` once after the existing editing migration, before deploying this app update. It copies the current Beers column of the October 1-29, 2026 report into a protected baseline table. Reapplying the migration keeps existing baseline values unchanged. The imported report ends October 29; the app does not claim to have October 30-31 data.

All dashboard count/percentage comparisons now come from that fixed October snapshot, including sorting, table values, summary totals, and CSV. October compared against itself starts at zero change. Future reports join the same per-location baseline by location ID; keep IDs stable during imports. Missing baselines yield no comparison. A zero baseline and zero current total give 0%; a nonzero current total against zero gives no defined percentage. Historical 2025 totals and original report percentages remain stored but are not the dashboard comparison.

Editors can change the current Beers total, name and address. Baseline values are read-only and percentages calculate automatically in the database; editing a later total does not move the baseline. The new save RPC retains atomic saves and concurrent-edit checks. The migration preserves legacy view fields so the currently deployed app continues working during rollout.

Tiles, read-only table totals, and volume summary values display a small CE number under Beers, calculated as Beers / 24, with two decimal places. Example: 1,488.00 Beers displays 62.00 CE. This is a presentation conversion; stored Beers are unchanged. Database migration execution and live verification are still pending. Local browser checks simulated the baseline snapshot, future changes, editing protection and CE display.

### November starts awaiting data

The baseline migration now also creates a separate November report (initial date November 1, 2026) with a null current total for each restaurant. Its null values are intentionally distinct from actual zero sales. October totals remain in both their original report and the protected baseline snapshot. Reapplying the SQL never resets existing November entries. Dating the initial empty report November 1 allows subsequent daily reports to supersede it under the normal latest-report rule.

The app displays 0.00 Beers / 0.00 CE and Awaiting November data until a value is entered. An entered zero yields -100% against a positive baseline. Clearing the value returns it to awaiting. Comparisons remain null while awaiting; summary count differences include only entered rows. The original October report is not the current November report.

## November 1-7 source report

`supabase/import-november-2026.sql` loads the 16 restaurant rows supplied for November 1-7 versus October 1-7, excluding Total and Bud Light rows. Run it after the October-baseline migration. All CE volume fields are multiplied by 24 before storing; source percentages remain exact. The source restaurant prior totals sum to 186.03 CE while the report Total shows 186.00; restaurant rows are authoritative here. The import adds Dave & Buster's Sugarloaf as a distinct location and does not replace Alpharetta.

The 16 current entries total 27.56 CE / 661.44 Beers: four nonzero entries and twelve actual zeros. All other known restaurants receive null current totals for this report, preserving awaiting status. With the original 22-location set there will be 23 total rows, 16 reported and 7 awaiting. Reimporting updates the same report rather than duplicating it. The import never writes the baseline table. Sugarloaf has no original October 1-29 baseline, so the app leaves its baseline comparison unavailable. The app continues using the fixed October 1-29 baseline, not this source's October 1-7 comparison column.

`python supabase/prepare_november_import.py` regenerates the SQL from `supabase/november-2026-report.json`. These actual report files remain local. Database execution is pending.

## Clean reload confirmed by the user

Use `supabase/reload-october-baseline.sql` for the latest reset/reload request. This one transaction replaces all restaurant, report, and baseline rows; it retains Auth accounts and permissions. It reloads the 22 supplied October restaurant rows, snapshots the October 2026 current-data column as the fixed baseline, and creates November with null current values for every restaurant. The user explicitly chose to start November awaiting data; do not run the previous November import afterward. Sugarloaf and other locations absent from the newly supplied October list are not included in this clean dataset.

Expected verification: 22 restaurants, 22 baselines totaling 12,070.32 Beers / 502.93 CE, 22 November rows, zero November entries, and 22 awaiting. The source's printed aggregate is 502.89 CE, but its individual restaurant rows sum to 502.93 CE. Restaurant rows are preserved without adjustment. `python supabase/prepare_baseline_reload.py` regenerates the reload SQL. Live execution remains pending until run in Supabase SQL Editor.

## Corrected 16-restaurant load (latest request)

The latest dataset supersedes the older October 1-29 baseline and blank-November reload. Run `supabase/load-october-november-2026.sql` against the emptied sales tables. Do not run the old reload-october-baseline.sql or import-november-2026.sql instead. This script loads only the 16 restaurants from the corrected report, using October 1-7 as the baseline and November 1-7 as actual reported values. It converts all CE volume columns to Beers once, leaves percentages unchanged, and preserves actual zeros. It replaces all restaurant/report/baseline rows in one transaction, retaining Auth accounts and editor permissions. This follows the user-authorized clean reload and also works when older sales rows remain.

Expected totals: 16 restaurants and 16 November entries; October baseline 186.03 CE / 4,464.72 Beers; November 27.56 CE / 661.44 Beers. The printed source Total says 186.00 CE, but the 16 restaurant October rows sum to 186.03 CE, so their values are preserved. Sugarloaf is included; Alpharetta is not. The zero-baseline comparison follows this source report's explicit +100% convention for positive November values. The script installs the baseline comparison view/save RPC, so the older October snapshot script is not required. The underlying tables, Beers conversion and editor permission helper must already exist. Live SQL execution remains pending.
