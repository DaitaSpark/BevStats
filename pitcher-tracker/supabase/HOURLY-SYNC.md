# Install hourly sales syncing

This runs inside Supabase with the app closed. No local computer stays on.
It is specifically configured for the October/November 2026 contest. Changed
columns or periods stop the import instead of silently loading a different report.

## 1. Apply the database migration

Open your existing Supabase project → SQL Editor → New query. Paste and run
`hourly-sync.sql`. This requires the existing November tables, dashboard baseline
view, and at least one November import. Do not run schema.sql or any clean-reload script.

The first successful sync selects the latest existing November report and pins its
ID in `bevstats_sync_status`. Later checks overwrite that same report's totals.
Earlier snapshots are retained; polling does not create additional snapshots.
New restaurants must be added/matched by an administrator before syncing can succeed.
Existing totals rows are created only if a location has no row in the selected report.

## 2. Deploy the function

Install Node.js LTS if it is not already installed. In PowerShell:

```powershell
cd C:\Users\jeffe\BevTracker\pitcher-tracker
npx supabase login
npx supabase link --project-ref YOUR_PROJECT_REF
npx supabase functions deploy sync-sales --no-verify-jwt
```

Your project reference is in the dashboard project URL. The files under
`supabase/functions/sync-sales` deploy together. The ExcelJS dependency is pinned
and used only by the server, not the public website.

In Supabase → Edge Functions → Secrets, add:

| Name | Value |
| --- | --- |
| `REPORT_URL` | The full Eagle Rock QuickLink supplied in chat |
| `SYNC_SECRET` | A newly generated random secret, at least 32 bytes |

Generate a secret locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
Store it in your password manager. Do not commit it or add it to browser assets.
The Secrets list displays a digest (hash), not the original value. Never copy
that digest into the test header; use the original generated secret.
For this workstation, the replacement secret is saved in the Git-ignored
`pitcher-tracker/.env.hourly-sync` file; keep that file private.
Supabase supplies `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` automatically.
JWT gateway verification is disabled because this function checks its own private
`x-sync-secret` header. Never remove that check.

## 3. Test before scheduling

In Edge Functions → sync-sales → Test, send a POST with body `{}` and header
`x-sync-secret` set to your secret. Expect HTTP 200 and a JSON response with
`report_id` and `changed_restaurants`. The first run may correct rounding because
Excel contains more precise quantities than the manually pasted reports.

Run the same test again. With unchanged source data and no manual edits,
`changed_restaurants` should be zero, while `last_success_at` advances:

```sql
select * from public.bevstats_sync_status;
select count(*) from public.bevstats_reports;
select count(*) from public.bevstats_report_totals;
```

Record counts should not increase on repeated runs. Check actual restaurant totals
in the app and confirm October baseline values remain unchanged. Test with an
incorrect x-sync-secret: expect 401 and no data/status changes. To test a failed
download, temporarily set REPORT_URL to `https://eaglerockdist.com/not-a-report`,
invoke once, and confirm last_error is populated while last_success_at and sales
remain unchanged. Restore the real REPORT_URL and invoke successfully afterward.

The report's totals must reconcile. Missing restaurants become awaiting, not zero.
Unknown or ambiguous names roll back the whole sales update. Manual sales edits
are replaced by the next successful sync; names, addresses, prices and fixed
October baselines are untouched. A renamed location requires a matching source
name (a persistent upstream-ID mapping would be needed to support independent names).

## 4. Enable the hourly schedule

Enable **Cron / pg_cron** and **pg_net** in the project's Integrations/Extensions.
In **Vault**, create these two secrets:

| Vault name | Value |
| --- | --- |
| `bevstats_function_url` | `https://YOUR_PROJECT_REF.supabase.co/functions/v1/sync-sales` |
| `bevstats_sync_secret` | Exactly the same value as SYNC_SECRET |

Run `schedule-hourly-sync.sql` in SQL Editor. It schedules minute zero of every
hour from 8 a.m. through 8 p.m. Eastern, inclusive (13 pulls per day).
Reapplying updates the named job instead of adding another. Cron checks hourly,
but the SQL only dispatches the function during that Eastern-time window.
America/New_York conversion automatically follows daylight-saving changes.

Verify the next run in Cron history and Edge Function logs. HTTP dispatch success
alone does not prove import success: check `last_success_at` and `last_error` too.

Stop polling at any time with:

```sql
select cron.unschedule('bevstats-hourly-sync');
```

No additional report files are saved. Cron retains execution history separately;
review/clean its history periodically according to your project's retention policy.
No email alerts are configured; failures appear in the app and the status table.

## 5. Publish the updated dashboard

The static assets have been rebuilt. Deploy the repository through the existing
Render workflow (`pitcher-tracker` root, `python build_static.py`, `static` publish
directory). The new frontend reads the pinned live report and the sync status.
It displays the last successful evaluation in America/New_York, including when
sales did not change. Failed checks leave that time unchanged and show a warning.
Before the first successful sync, it continues showing the existing daily snapshot.
An already open page gets the new status on its next data reload/page refresh.

The source cache timestamp is retained as raw text because its timezone is not
specified by the workbook. It is not presented as a verified sales cutoff date.
The old daily report date is retained for historical compatibility; once sync is
active, the UI labels the October/November reporting window separately from the
evaluation time. Stop using dated manual imports once hourly sync is active.

## Validation and future months

Existing app checks: `python -m unittest -v` from pitcher-tracker.
With Deno installed, parser checks:

```powershell
deno test --allow-env --allow-read supabase/functions/sync-sales/report_test.ts
deno check supabase/functions/sync-sales/index.ts
```

Function deployment, workbook parsing in the hosted runtime, database migration,
and the two-run/failed-download checks above must pass before enabling Cron.
This implementation does not automatically roll over to December. For another
contest period, revise the period checks, report selection and baseline policy,
then validate against the new report before resuming the schedule.

Official references: [scheduled functions](https://supabase.com/docs/guides/functions/schedule-functions),
[function configuration](https://supabase.com/docs/guides/functions/function-configuration).

## Activation status ? November 6, 2026

Vault configuration and extensions are installed on BevStats. The named
`bevstats-hourly-sync` job is active with schedule `0 * * * *`. A manual execution
of the exact scheduled HTTP command returned HTTP 200 with zero changed
restaurants. The next natural hourly execution should still be checked in Cron
history. Dashboard publication remains a separate step.

## Daytime schedule ? November 11, 2026

Polling is restricted to 8 a.m.?8 p.m. America/New_York, inclusive, every day.
No report download or Edge Function invocation occurs from 9 p.m. through 7 a.m.
Cron still evaluates a small SQL time check hourly. The named job is reused.
