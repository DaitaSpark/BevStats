-- Convert stored volumes exactly once. Percentages, prices, dates and IDs are unchanged.
-- Run in Supabase SQL Editor before deploying the Beers dashboard.
begin;
lock table public.bevstats_report_totals in access exclusive mode;
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema='public'
             and table_name='bevstats_report_totals' and column_name='current_case_equivalents') then
    alter table public.bevstats_report_totals rename column prior_case_equivalents to prior_beers;
    alter table public.bevstats_report_totals rename column current_case_equivalents to current_beers;
    alter table public.bevstats_report_totals rename column reported_change to reported_change_beers;
    update public.bevstats_report_totals set prior_beers=prior_beers*24,
      current_beers=current_beers*24, reported_change_beers=reported_change_beers*24;
  end if;
end $$;
-- Keep old case-equivalent API fields for the currently deployed app during rollout.
-- New app reads the appended beer columns directly, without multiplying in JavaScript.
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
notify pgrst, 'reload schema';
commit;
select count(*) as locations, sum(current_beers) as current_beers,
 sum(prior_beers) as prior_beers from public.bevstats_dashboard;
