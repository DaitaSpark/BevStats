# Fill the Pitcher

The production app uses shared Supabase report data. Anyone can view Beers and prior-year comparisons without signing in. Only the designated admin, jeff.eckard@daitaspark.com, can add/edit database rows after email-link verification and owner assignment. Owner editing controls and daily import UI are pending.

See the [repository setup guide](../README.md) for schema setup, the initial 22-restaurant import, admin assignment, allowed sign-in redirect URLs, local preview, and hosting instructions. The supplied URL and publishable key are in supabase-public.json; no secret keys are stored there.

The tables, initial report, and admin assignment are configured in Supabase; the local preview has been verified against the live data. The production app does not load sample data or fall back to browser-local demo records.

For the Beers update, run `supabase/convert-to-beers.sql` on the existing database before deployment. Stored volumes are multiplied by 24 exactly once; percentage changes and prices stay unchanged. See the repository guide for rollout details.

Location tiles and the detail table show current Beers totals and percentage-only comparisons against the report's prior-year period. Prior-year counts and count differences remain stored and available in CSV export, but are hidden in these location views. This comparison is not against a previous daily upload.

Displayed percentage comparisons round to whole percentages in tiles and the table (for example, 12.50% displays as +13%). Database values and CSV export retain their original precision.

Use Total Beers / % change above the board to sort tiles descending by current report volume or the source percentage change. Total Beers is the default. Percentage ties sort by Beers, then location name; missing percentages appear last. Switching sort resets the tile page and updates ranks and address disclosures. The table and CSV keep their total-Beers order.
