# SEC Championship Ticket Giveaway

The production app uses shared Supabase report data. Anyone can view Beers and prior-year comparisons without signing in. Jeff (jeff.eckard@daitaspark.com) and Corey (corey.eckard@eaglerocks.com) can sign in with Admin using their email and password, then edit and save the table. Daily import UI remains pending.

See the [repository setup guide](../README.md) for schema setup, the initial 22-restaurant import, admin assignment, allowed sign-in redirect URLs, local preview, and hosting instructions. The supplied URL and publishable key are in supabase-public.json; no secret keys are stored there.

The tables, initial report, and admin assignment are configured in Supabase; the local preview has been verified against the live data. The production app does not load sample data or fall back to browser-local demo records.

For the Beers update, run `supabase/convert-to-beers.sql` on the existing database before deployment. Stored volumes are multiplied by 24 exactly once; percentage changes and prices stay unchanged. See the repository guide for rollout details.

Location tiles and the detail table show current Beers totals and percentage-only comparisons against the report's prior-year period. Prior-year counts and count differences remain stored and available in CSV export, but are hidden in these location views. This comparison is not against a previous daily upload.

Displayed percentage comparisons round to whole percentages in tiles and the table (for example, 12.50% displays as +13%). Database values and CSV export retain their original precision.

Use Total Beers / % change above the board to sort tiles descending by current report volume or the source percentage change. Total Beers is the default. Percentage ties sort by Beers, then location name; missing percentages appear last. Switching sort resets the tile page and updates ranks and address disclosures. The table and CSV keep their total-Beers order.

## Restored table editing

Run `supabase/enable-table-editing.sql` in Supabase SQL Editor once before using this update. Ensure both authorized emails exist as confirmed Supabase Auth users with individual passwords. Admin sign-in does not send email or redirect to a verification link. Everyone else continues to view without signing in. Use Edit table ? Save changes for location/address, current/prior Beers, and percentage corrections. Save is atomic and detects concurrent changes. No sales data is changed by the permission migration itself.

For an existing account without a password, use Admin ? enter email ? Set / reset password. Open the recovery email link and choose/confirm a password in the app. Locally, allow http://localhost:8001/ in Supabase Auth redirect URLs first. No account deletion or new SQL is needed. Routine sign-in still uses email/password.
