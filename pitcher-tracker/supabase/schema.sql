-- Apply in the intended Supabase project's SQL editor. No existing tables/data are deleted.
begin;
create table public.bevstats_owner (
  singleton boolean primary key default true check (singleton),
  user_id uuid not null unique references auth.users(id) on delete cascade
);
create table public.bevstats_locations (
  id bigint generated always as identity primary key,
  name text not null check (length(trim(name)) between 1 and 200),
  address text not null,
  salesperson text not null default '',
  beer_price numeric(10,2) check (beer_price >= 0),
  unique(name, address)
);
create table public.bevstats_reports (
  id bigint generated always as identity primary key,
  prior_start date not null,
  prior_end date not null,
  current_start date not null,
  current_end date not null,
  loaded_at timestamptz not null default now(),
  check(prior_end >= prior_start),
  check(current_end >= current_start),
  unique(prior_start, prior_end, current_start, current_end)
);
create table public.bevstats_report_totals (
  report_id bigint not null references public.bevstats_reports(id),
  location_id bigint not null references public.bevstats_locations(id),
  prior_beers numeric(16,2) check (prior_beers >= 0),
  current_beers numeric(16,2) check (current_beers >= 0),
  reported_change_beers numeric(16,2),
  reported_percent numeric(16,2),
  primary key(report_id, location_id)
);
alter table public.bevstats_owner enable row level security;
alter table public.bevstats_locations enable row level security;
alter table public.bevstats_reports enable row level security;
alter table public.bevstats_report_totals enable row level security;
create policy own_owner_record on public.bevstats_owner for select to authenticated
  using (user_id = (select auth.uid()));
create policy public_read_locations on public.bevstats_locations for select to anon, authenticated using (true);
create policy owner_insert_locations on public.bevstats_locations for insert to authenticated with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create policy owner_update_locations on public.bevstats_locations for update to authenticated using (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid()))) with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create policy public_read_reports on public.bevstats_reports for select to anon, authenticated using (true);
create policy owner_insert_reports on public.bevstats_reports for insert to authenticated with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create policy owner_update_reports on public.bevstats_reports for update to authenticated using (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid()))) with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create policy public_read_report_totals on public.bevstats_report_totals for select to anon, authenticated using (true);
create policy owner_insert_report_totals on public.bevstats_report_totals for insert to authenticated with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create policy owner_update_report_totals on public.bevstats_report_totals for update to authenticated using (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid()))) with check (exists(select 1 from public.bevstats_owner where user_id = (select auth.uid())));
create or replace view public.bevstats_dashboard with (security_invoker = true) as
select l.id, l.name, l.address, l.salesperson, l.beer_price,
 (t.prior_beers / 24)::numeric(14,2) as prior_case_equivalents,
 (t.current_beers / 24)::numeric(14,2) as current_case_equivalents,
 (t.reported_change_beers / 24)::numeric(14,2) as reported_change,
 t.reported_percent,
 r.id as report_id, r.prior_start, r.prior_end, r.current_start, r.current_end, r.loaded_at,
 t.prior_beers, t.current_beers, t.reported_change_beers
from public.bevstats_report_totals t
join public.bevstats_locations l on l.id = t.location_id
join public.bevstats_reports r on r.id = t.report_id;
revoke all on public.bevstats_owner, public.bevstats_locations, public.bevstats_reports,
 public.bevstats_report_totals, public.bevstats_dashboard from anon, authenticated;
grant select on public.bevstats_locations, public.bevstats_reports,
 public.bevstats_report_totals, public.bevstats_dashboard to anon, authenticated;
grant select on public.bevstats_owner to authenticated;
grant insert, update on public.bevstats_locations, public.bevstats_reports,
 public.bevstats_report_totals to authenticated;
grant usage on sequence public.bevstats_locations_id_seq, public.bevstats_reports_id_seq to authenticated;
-- Assign the single owner through the SQL editor after creating their Auth account.
-- insert into public.bevstats_owner(user_id) values ('CONFIRMED-OWNER-AUTH-UUID');
-- Browser roles cannot insert/update/delete the owner record or delete sales rows.
commit;
