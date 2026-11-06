-- Run once (safe to reapply) after convert-to-beers.sql.
begin;
create or replace function public.bevstats_can_edit() returns boolean
language sql stable security definer set search_path = '' as $$
 select exists(select 1 from auth.users u where u.id = auth.uid()
   and u.email_confirmed_at is not null and lower(u.email) in
   ('jeff.eckard@daitaspark.com','corey.eckard@eaglerocks.com'));
$$;
revoke all on function public.bevstats_can_edit() from public, anon;
grant execute on function public.bevstats_can_edit() to authenticated;
-- Replace the former single-owner write rules. Public read policies remain.
do $$
declare suffix text;
begin
 foreach suffix in array array['locations','reports','report_totals'] loop
  execute format('drop policy if exists %I on public.%I','owner_insert_'||suffix,'bevstats_'||suffix);
  execute format('drop policy if exists %I on public.%I','owner_update_'||suffix,'bevstats_'||suffix);
  execute format('drop policy if exists editor_insert on public.bevstats_%I',suffix);
  execute format('drop policy if exists editor_update on public.bevstats_%I',suffix);
  execute format('create policy editor_insert on public.bevstats_%I for insert to authenticated with check ((select public.bevstats_can_edit()))',suffix);
  execute format('create policy editor_update on public.bevstats_%I for update to authenticated using ((select public.bevstats_can_edit())) with check ((select public.bevstats_can_edit()))',suffix);
 end loop;
end $$;
create or replace function public.bevstats_save_edits(p_report_id bigint,p_changes jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare item jsonb; old_row record; new_prior numeric; new_current numeric; new_percent numeric;
 changed_count integer := 0;
begin
 if not public.bevstats_can_edit() then raise exception 'Only Jeff and Corey can edit this report.' using errcode='42501'; end if;
 if jsonb_typeof(p_changes) is distinct from 'array' or jsonb_array_length(p_changes)>1000 then raise exception 'Invalid edit list'; end if;
 if exists(select 1 from jsonb_array_elements(p_changes) x group by x->>'id' having count(*)>1) then raise exception 'Duplicate location edits'; end if;
 for item in select value from jsonb_array_elements(p_changes) order by (value->>'id')::bigint loop
  if jsonb_typeof(item->'name') is distinct from 'string' or length(trim(item->>'name')) not between 1 and 200
    or jsonb_typeof(item->'address') is distinct from 'string' or length(item->>'address')>200 then raise exception 'Enter a valid name and address'; end if;
  if coalesce(jsonb_typeof(item->'previous_cans'),'missing') not in ('number','null')
   or coalesce(jsonb_typeof(item->'cans'),'missing') not in ('number','null')
   or coalesce(jsonb_typeof(item->'reported_percent'),'missing') not in ('number','null') then raise exception 'Enter valid numeric totals and percentage'; end if;
  new_prior := (item->>'previous_cans')::numeric; new_current := (item->>'cans')::numeric;
  new_percent := (item->>'reported_percent')::numeric;
  if new_prior<0 or new_current<0 or new_prior>10000000000 or new_current>10000000000
    or abs(new_percent)>1000000000 or new_prior<>round(new_prior,2) or new_current<>round(new_current,2)
    or new_percent<>round(new_percent,2) then raise exception 'Totals must be nonnegative with at most two decimals'; end if;
  select l.name,l.address,t.prior_beers,t.current_beers,t.reported_percent,t.reported_change_beers
   into old_row from public.bevstats_locations l join public.bevstats_report_totals t on t.location_id=l.id
   where t.report_id=p_report_id and l.id=(item->>'id')::bigint for update of l,t;
  if not found then raise exception 'Report location no longer exists. Reload and retry.'; end if;
  if old_row.name is distinct from (item->'original'->>'name')
   or old_row.address is distinct from (item->'original'->>'address')
   or old_row.prior_beers is distinct from (item->'original'->>'previous_cans')::numeric
   or old_row.current_beers is distinct from (item->'original'->>'cans')::numeric
   or old_row.reported_percent is distinct from (item->'original'->>'reported_percent')::numeric then
    raise exception 'Another editor changed this location. Cancel and reload before saving.' using errcode='40001';
  end if;
  update public.bevstats_locations set name=trim(item->>'name'),address=trim(item->>'address') where id=(item->>'id')::bigint;
  update public.bevstats_report_totals set prior_beers=new_prior,current_beers=new_current,reported_percent=new_percent,
    reported_change_beers=case when old_row.prior_beers is distinct from new_prior or old_row.current_beers is distinct from new_current
      then new_current-new_prior else old_row.reported_change_beers end
   where report_id=p_report_id and location_id=(item->>'id')::bigint;
  changed_count := changed_count+1;
 end loop;
 return jsonb_build_object('ok',true,'updated',changed_count);
end $$;
revoke all on function public.bevstats_save_edits(bigint,jsonb) from public,anon;
grant execute on function public.bevstats_save_edits(bigint,jsonb) to authenticated;
notify pgrst,'reload schema';
commit;
