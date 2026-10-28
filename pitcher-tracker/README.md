# Fill the Pitcher

**Current hosting target: Render Static Site.** See [the repository README](../README.md) for the no-startup-delay browser demo. The Python/SQLite instructions below describe the optional backend, not requirements for static hosting.

An unofficial Bud Light delivered-can dashboard for Corey and colleagues. Responsive glass pitchers compare delivered volume across locations and show each location's address, beer price, and change since its previous saved entry.

## Run

Requires Python 3.10 or later; no packages to install.

```powershell
cd C:\Users\jeffe\BevTracker\pitcher-tracker
python server.py
```

Open http://localhost:8000. Keep the terminal running. The first start creates 18 sample locations with sales and salespeople. The initial modal lets you create the first account; choose a username and password of at least 4 characters. Later visits require sign-in unless an existing session is still valid. **Start fresh** removes sample data. Use **Edit table** to add locations, enter each address and beer price, and update cumulative delivered-can totals. Click **Save changes** to update the pitchers. The volume increase compares the current total with the prior saved total; existing records begin showing a change after their next save. Convert cases to cans before entering totals.

Records persist in `sales.sqlite3`, shared by browsers connected to this server. Other viewers refresh every 30 seconds. Back up that file while the server is stopped. CSV export downloads the saved table. Editing is a full-table save; coordinate one editor at a time to avoid overwriting another person's changes.

## Hosting and team access

This is a runnable, deployable Python application; it has not been published. The available Sites workflow requires Node.js, which was unavailable in the development environment. This Python server needs a Python-capable host rather than static-only hosting.

For free sample-data hosting, follow the demo settings in the [repository README](../README.md). For durable storage on a paid hosted deployment, run `python server.py` with `HOST=0.0.0.0`, set `PORT` to the host's assigned port, and set `BEVTRACKER_DB` to a file on a persistent disk. Run one application instance against that disk. Serve behind HTTPS before exposing it outside a trusted network. Sign-in is required for reading or updating sales. All signed-in users can edit; there are no separate viewer/editor roles. Provision the first account locally before exposing a new empty database publicly. At Render, forwarded HTTPS requests receive Secure session cookies. Python's built-in HTTP server is suitable for a local pilot; use a production HTTP reverse proxy for hosting.

## Future delivered-sales report

The UI reads `GET /api/locations`, returning location records with address, beer price, previous delivered-can total, and salesperson fields. Manual saves use `POST /api/locations` with the full location table and replace it transactionally while retaining IDs and recording each prior total. Future report ingestion should validate delivered status and units, and deduplicate reports before updating totals. Report ingestion is not implemented yet.

External Google Fonts are optional; the page falls back to system fonts when offline. All pitcher graphics are CSS, with no image dependencies. Decorative beer motion uses the dashboard's Animation: On/Off preference.

The compact header keeps the pour board near the top of the page. On initial load, nonempty pitchers pour and fill together over about 4.6 seconds. Automatic data refreshes do not replay the pour. Animation: Off shows final levels immediately.

Locations and rank labels are ordered by delivered cans, highest first (ties use location name). The dashboard summarizes delivered cans, volume increase, locations, and average beer price. Addresses are tucked behind a location-pin button on each pitcher card and can be expanded on demand. Beer prices are optional, editable per location, and exported with address and volume change in the CSV.

The browser-tab favicon is a blue square with a gold beer pitcher. Its editable source is `favicon.svg`; the page embeds it as an SVG data URL so no additional asset request is needed.

## Browsing a large team

Supports up to 1,000 saved locations. Search location names, addresses, and salespeople, and filter by salesperson. Pitcher view displays 12 locations per page and compact table view displays 25. Rankings use overall delivered cans; summary totals always cover all locations. CSV export includes every saved location, address, salesperson, volume change, and beer price. Existing databases gain the new fields automatically on startup without losing records.

Use Edit table to enter addresses, beer prices, and salespeople. Filters pause while editing so you can work through all locations, 25 per page, without edited rows disappearing. Unsaved edits persist when changing pages; Save changes saves all pages together. Coordinate one editor at a time.

## Accounts and verification

Passwords are salted and hashed with PBKDF2-SHA256 (600,000 iterations). Sessions are stored as token hashes in SQLite and expire after eight hours. The browser receives an HttpOnly, SameSite=Strict cookie; signing out revokes that session. Failed authentication is rate-limited per IP to ten attempts per ten minutes (in memory, reset on process restart). The header displays the signed-in account's username and initials.

To provision an additional colleague account from the server terminal:

```powershell
python server.py --create-user
```

The command prompts for a username, display name, and password without echoing the password. Account management and password recovery screens are not implemented. There is no shared default password.

To fill in missing demonstration locations in a database still labeled as sample data, run `python server.py --seed-samples`. This preserves existing sales numbers and populated metadata, adds missing sample locations, and refuses to run on real sales data. Normal startup does not repopulate a cleared table.

Run checks from this directory with `python -m unittest -v`. Tests use temporary databases and cover sign-in, account setup, session expiration, sign-out, protected reads/writes, cross-origin rejection, password hashing, login rate limiting, 400-location storage, and preserving sample edits.

Pitcher tiles use six columns at desktop widths of 1,100px and above, displaying a full 12-location page in two rows. Smaller screens step down to four, three, or two columns; the smallest screens use one.

The desktop header, summary, and filters use compact rows. Pitcher height adapts to viewport height to keep the two-row board visible on typical desktop windows; full location names remain available as tooltips. Browser zoom, unusually short windows, and narrower layouts may still require scrolling.

Stat labels use larger, bold text. Each pitcher card places its location name and address above the graphic, with a full-name tooltip, and shows beer price and change since the previous entry below it. Pitcher graphics are contained within their stage so they do not overlap labels or sales figures.

## Render Free demo mode

Set `HOST=0.0.0.0`, `BEVSTATS_DEMO_MODE=1`, `BEVSTATS_LOGIN_USERNAME`, and a secret `BEVSTATS_LOGIN_PASSWORD` of 4-256 characters. Optionally set `BEVSTATS_LOGIN_NAME`. Remove the old `BEVTRACKER_DB=/var/data/sales.sqlite3` setting. No disk is needed. Demo mode refuses startup if credentials are missing or invalid, avoiding an unclaimed public account setup after every reset.

The server restores its 18 sample records and configured account when temporary storage is lost. Sales edits persist only while that temporary filesystem survives. The sign-in modal explains demo storage. CSV export remains available; restoring a CSV through the UI is not yet supported. This does not provide durable shared storage for real delivery reports.

Top demo/sample banners are removed. Start fresh and Restore samples are available alongside the detail-table controls. Nonempty pitchers pour together on initial load and when the displayed page changes, with larger continuously rising bubbles. Replay pour restarts the fill on demand, including as an explicit motion request with reduced-motion settings. Unchanged background refreshes preserve the existing pitcher elements instead of interrupting the animation.

The static demo currently bypasses authentication and defaults to Corey. The modal, password handling, prior browser accounts, and backend authentication are retained. Set `window.BEVSTATS_DEMO_AUTH_ENABLED` to `true` in `static-demo.js` and rebuild to restore the demo sign-in flow. Backend authentication remains enabled independently.

Dashboard stats use a native expand/collapse control and start collapsed on every page load. Pour animations wait until their cards enter the viewport, so mobile users see the fill when scrolling down rather than missing it while the controls are onscreen. The dashboard motion setting controls decorative beer animation independently of the system motion preference.

Search and filters are also collapsed on initial load. The Pitchers/Table switch stays visible outside the collapsed search section so both views remain accessible.

Beer motion is enabled by default, including on phones with a system reduced-motion preference. The Animation: On/Off control stores a browser-local choice and disables both automatic pours and rising bubbles when Off. Replay pour turns motion On. Visibility-triggered pours restart their keyframes instead of resuming a paused animation, and bubbles continue after filling finishes.
