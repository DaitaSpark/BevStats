-- Apply once to the existing November dashboard. Safe to reapply.
begin;
create table if not exists public.bevstats_sync_status (
 id boolean primary key default true check(id),
 report_id bigint references public.bevstats_reports(id),
 last_attempt_at timestamptz, last_success_at timestamptz,
 source_cache_time text, last_error text
);
insert into public.bevstats_sync_status(id) values(true) on conflict do nothing;
alter table public.bevstats_sync_status enable row level security;
drop policy if exists public_read_sync_status on public.bevstats_sync_status;
create policy public_read_sync_status on public.bevstats_sync_status for select to anon,authenticated using(true);
revoke all on public.bevstats_sync_status from anon,authenticated;
grant select on public.bevstats_sync_status to anon,authenticated;

create or replace function public.bevstats_sync_attempt(p_started timestamptz)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
begin
 update public.bevstats_sync_status set last_attempt_at=p_started
 where id and (last_attempt_at is null or last_attempt_at<p_started);
 return '{}'::jsonb;
end $$;
create or replace function public.bevstats_sync_failure(p_started timestamptz,p_error text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
begin
 update public.bevstats_sync_status set last_error=left(p_error,200)
 where id and last_attempt_at=p_started;
 return '{}'::jsonb;
end $$;

create or replace function public.bevstats_sync_sales(p_started timestamptz,p_rows jsonb,p_cache_time text)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare
 target bigint; rec record; matches bigint[]; changed integer:=0; affected integer;
begin
 perform pg_advisory_xact_lock(hashtext('bevstats-daily-import'));
 perform 1 from public.bevstats_sync_status where id for update;
 if (select last_attempt_at>p_started from public.bevstats_sync_status where id) then
  return jsonb_build_object('skipped','superseded');
 end if;
 if jsonb_typeof(p_rows)<>'array' or jsonb_array_length(p_rows) not between 1 and 1000 then
  raise exception 'Invalid rows';
 end if;
 if exists(select 1 from jsonb_to_recordset(p_rows) as x(name text,current_beers numeric,prior_beers numeric,reported_change_beers numeric,reported_percent numeric)
  where name is null or trim(name)='' or current_beers is null or prior_beers is null or reported_change_beers is null or reported_percent is null
   or current_beers<0 or prior_beers<0 or current_beers::text in ('NaN','Infinity','-Infinity') or prior_beers::text in ('NaN','Infinity','-Infinity')) then raise exception 'Invalid values'; end if;
 if exists(select 1 from jsonb_array_elements(p_rows) x group by lower(trim(x->>'name')) having count(*)>1) then raise exception 'Duplicate rows'; end if;
 select report_id into target from public.bevstats_sync_status where id;
 if target is null then
  select id into target from public.bevstats_reports
  where prior_start='2026-10-01' and prior_end='2026-10-31' and current_start='2026-11-01'
  order by current_end desc,loaded_at desc,id desc limit 1;
  if target is null then raise exception 'Import the initial November report first'; end if;
 end if;
 -- Reuse this report forever for November; no hourly/daily report inserts.
 for rec in select * from jsonb_to_recordset(p_rows) as x(name text,current_beers numeric,prior_beers numeric,reported_change_beers numeric,reported_percent numeric) loop
  select array_agg(id) into matches from public.bevstats_locations
   where lower(regexp_replace(trim(name),'\s+',' ','g'))=lower(rec.name);
  if coalesce(cardinality(matches),0)<>1 then raise exception 'Unknown or ambiguous restaurant: %',rec.name; end if;
 end loop;
 insert into public.bevstats_report_totals(report_id,location_id)
 select target,id from public.bevstats_locations on conflict do nothing;
 for rec in select * from jsonb_to_recordset(p_rows) as x(name text,current_beers numeric,prior_beers numeric,reported_change_beers numeric,reported_percent numeric) loop
  update public.bevstats_report_totals t set current_beers=rec.current_beers,prior_beers=rec.prior_beers,
   reported_change_beers=rec.reported_change_beers,reported_percent=rec.reported_percent
  from public.bevstats_locations l where t.report_id=target and t.location_id=l.id
   and lower(regexp_replace(trim(l.name),'\s+',' ','g'))=lower(rec.name)
   and (t.current_beers,t.prior_beers,t.reported_change_beers,t.reported_percent)
    is distinct from (rec.current_beers,rec.prior_beers,rec.reported_change_beers,rec.reported_percent);
  get diagnostics affected=row_count; changed:=changed+affected;
 end loop;
 update public.bevstats_report_totals t set current_beers=null,prior_beers=null,reported_change_beers=null,reported_percent=null
 where report_id=target and not exists(select 1 from public.bevstats_locations l, jsonb_array_elements(p_rows) x
  where l.id=t.location_id and lower(regexp_replace(trim(l.name),'\s+',' ','g'))=lower(x->>'name'))
  and (current_beers is not null or prior_beers is not null or reported_change_beers is not null or reported_percent is not null);
 get diagnostics affected=row_count; changed:=changed+affected;
 update public.bevstats_reports set loaded_at=now() where id=target and changed>0;
 update public.bevstats_sync_status set report_id=target,last_success_at=now(),source_cache_time=p_cache_time,last_error=null where id;
 return jsonb_build_object('changed_restaurants',changed,'report_id',target);
end $$;

revoke all on function public.bevstats_sync_attempt(timestamptz) from public,anon,authenticated;
revoke all on function public.bevstats_sync_failure(timestamptz,text) from public,anon,authenticated;
revoke all on function public.bevstats_sync_sales(timestamptz,jsonb,text) from public,anon,authenticated;
grant execute on function public.bevstats_sync_attempt(timestamptz) to service_role;
grant execute on function public.bevstats_sync_failure(timestamptz,text) to service_role;
grant execute on function public.bevstats_sync_sales(timestamptz,jsonb,text) to service_role;
notify pgrst,'reload schema';
commit;
