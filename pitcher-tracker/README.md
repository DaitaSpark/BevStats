# SEC Championship Ticket Giveaway

The current dashboard reports November 2026 month-to-date against the full October 2026 baseline. It selects the latest daily snapshot by its as-of date and displays the database's actual reporting periods. The latest supplied report is as of November 2, 2026.

Use `supabase/import-november-02-2026.sql` for this update. Routine daily imports retain report history and location IDs; they do not wipe the database. The October column in this source corrects the original partial baseline. Later daily sources preserve the full-month baseline by default.

Volumes display in Beers with a small CE number underneath (Beers / 24). Percentage comparisons round to whole numbers. Null current totals show awaiting data, while a reported zero is treated as an actual value. Total Beers / % change sorts the tiles highest first; missing percentages appear last.

Jeff and Corey can sign in using Admin and their individual Supabase Auth email/password to edit current totals, names, and addresses. Baselines are read-only. Set / reset password handles first-password setup and recovery for existing accounts. Public viewing requires no login.

See the [repository guide](../README.md) for build, hosting, import, access, and validation instructions. Older local setup/import files are retained for historical reference and are not part of the current daily-import workflow.

## Hourly live-report sync

See [hourly sync setup](supabase/HOURLY-SYNC.md) for the migration, Edge Function deployment, manual validation, hourly Cron schedule, and dashboard timestamp. The sync function is deployed and hourly polling is active as of November 6, 2026. The dashboard assets include the last-successful-check timestamp.
