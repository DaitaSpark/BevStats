# Fill the Pitcher

The production app uses shared Supabase report data. Anyone can view case equivalents and prior-year comparisons without signing in. Only the designated admin, jeff.eckard@daitaspark.com, can add/edit database rows after email-link verification and owner assignment. Owner editing controls and daily import UI are pending.

See the [repository setup guide](../README.md) for schema setup, the initial 22-restaurant import, admin assignment, allowed sign-in redirect URLs, local preview, and hosting instructions. The supplied URL and publishable key are in supabase-public.json; no secret keys are stored there.

The tables, initial report, and admin assignment are configured in Supabase; the local preview has been verified against the live data. The production app does not load sample data or fall back to browser-local demo records.
