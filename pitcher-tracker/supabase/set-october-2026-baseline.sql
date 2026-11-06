-- Run after enable-table-editing.sql. Snapshots October 1-29, 2026 exactly once.
begin;
create table if not exists public.bevstats_baselines (
 location_id bigint primary key references public.bevstats_locations(id),
 source_report_id bigint not null references public.bevstats_reports(id),
 baseline_start date not null,
 baseline_end date not null,
 baseline_beers numeric(16,2) check (baseline_beers>=0)
);
alter table public.bevstats_baselines enable row level security;
revoke all on public.bevstats_baselines from anon,authenticated;
grant select on public.bevstats_baselines to anon,authenticated;
drop policy if exists public_read_baselines on public.bevstats_baselines;
create policy public_read_baselines on public.bevstats_baselines for select to anon,authenticated using(true);
do $$
begin
 if not exists(select 1 from public.bevstats_reports where current_start='2026-10-01' and current_end='2026-10-29') then
  raise exception 'The October 1-29, 2026 source report is missing. No baseline has been created.';
 end if;
end $$;
insert into public.bevstats_baselines(location_id,source_report_id,baseline_start,baseline_end,baseline_beers)
select t.location_id,r.id,r.current_start,r.current_end,t.current_beers
from public.bevstats_report_totals t join public.bevstats_reports r on r.id=t.report_id
where r.id=(select id from public.bevstats_reports where current_start='2026-10-01' and current_end='2026-10-29' order by loaded_at desc,id desc limit 1)
on conflict(location_id) do nothing;
-- Start November separately. NULL means no entry yet; a saved zero is real data.
-- Date the initial empty report Nov 1 so later daily reports supersede it naturally.
insert into public.bevstats_reports(prior_start,prior_end,current_start,current_end)
values('2026-10-01','2026-10-29','2026-11-01','2026-11-01')
on conflict(prior_start,prior_end,current_start,current_end) do nothing;
insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent)
select r.id,b.location_id,b.baseline_beers,null,null,null
from public.bevstats_baselines b cross join public.bevstats_reports r
where r.prior_start='2026-10-01' and r.prior_end='2026-10-29'
 and r.current_start='2026-11-01' and r.current_end='2026-11-01'
on conflict(report_id,location_id) do nothing;
-- Legacy report fields are preserved for the current deployment during rollout.
create or replace view public.bevstats_dashboard with (security_invoker=true) as
select l.id,l.name,l.address,l.salesperson,l.beer_price,
 (t.prior_beers/24)::numeric(14,2) as prior_case_equivalents,
 (t.current_beers/24)::numeric(14,2) as current_case_equivalents,
 (t.reported_change_beers/24)::numeric(14,2) as reported_change,t.reported_percent,
 r.id as report_id,r.prior_start,r.prior_end,r.current_start,r.current_end,r.loaded_at,
 t.prior_beers,t.current_beers,t.reported_change_beers,
 b.baseline_beers,b.baseline_start,b.baseline_end,
 t.current_beers-b.baseline_beers as baseline_change_beers,
 case when b.baseline_beers>0 then round((t.current_beers-b.baseline_beers)*100/b.baseline_beers,2)
      when b.baseline_beers=0 and t.current_beers=0 then 0::numeric else null::numeric end as baseline_percent
from public.bevstats_report_totals t join public.bevstats_locations l on l.id=t.location_id
join public.bevstats_reports r on r.id=t.report_id
left join public.bevstats_baselines b on b.location_id=t.location_id;
create or replace function public.bevstats_save_baseline_edits(p_report_id bigint,p_changes jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare item jsonb; old_row record; new_current numeric; changed_count integer:=0;
begin
 if not public.bevstats_can_edit() then raise exception 'Only Jeff and Corey can edit this report.' using errcode='42501'; end if;
 if jsonb_typeof(p_changes) is distinct from 'array' or jsonb_array_length(p_changes)>1000 then raise exception 'Invalid edit list'; end if;
 if exists(select 1 from jsonb_array_elements(p_changes) x group by x->>'id' having count(*)>1) then raise exception 'Duplicate location edits'; end if;
 for item in select value from jsonb_array_elements(p_changes) order by (value->>'id')::bigint loop
  if jsonb_typeof(item->'name') is distinct from 'string' or length(trim(item->>'name')) not between 1 and 200
    or jsonb_typeof(item->'address') is distinct from 'string' or length(item->>'address')>200 then raise exception 'Enter a valid name and address'; end if;
  if coalesce(jsonb_typeof(item->'cans'),'missing') not in ('number','null') then raise exception 'Enter valid Beers'; end if;
  new_current:=(item->>'cans')::numeric;
  if new_current<0 or new_current>10000000000 or new_current<>round(new_current,2) then raise exception 'Beers must be nonnegative with at most two decimals'; end if;
  select l.name,l.address,t.current_beers into old_row
   from public.bevstats_locations l join public.bevstats_report_totals t on t.location_id=l.id
   where t.report_id=p_report_id and l.id=(item->>'id')::bigint for update of l,t;
  if not found then raise exception 'Report location no longer exists. Reload and retry.'; end if;
  if old_row.name is distinct from (item->'original'->>'name')
    or old_row.address is distinct from (item->'original'->>'address')
    or old_row.current_beers is distinct from (item->'original'->>'cans')::numeric then
    raise exception 'Another editor changed this location. Cancel and reload before saving.' using errcode='40001';
  end if;
  update public.bevstats_locations set name=trim(item->>'name'),address=trim(item->>'address') where id=(item->>'id')::bigint;
  update public.bevstats_report_totals set current_beers=new_current where report_id=p_report_id and location_id=(item->>'id')::bigint;
  changed_count:=changed_count+1;
 end loop;
 return jsonb_build_object('ok',true,'updated',changed_count);
end $$;
revoke all on function public.bevstats_save_baseline_edits(bigint,jsonb) from public,anon;
grant execute on function public.bevstats_save_baseline_edits(bigint,jsonb) to authenticated;
notify pgrst,'reload schema';
commit;
select count(*) as locations,sum(baseline_beers) as baseline_beers from public.bevstats_baselines;
select count(*) as november_locations,count(t.current_beers) as november_entries
from public.bevstats_report_totals t join public.bevstats_reports r on r.id=t.report_id
where r.current_start='2026-11-01' and r.current_end='2026-11-01';
