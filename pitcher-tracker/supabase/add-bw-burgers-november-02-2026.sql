-- Add/correct only B&W for the November 2 report. Other restaurant data is untouched.
begin;
select pg_advisory_xact_lock(hashtext('bevstats-daily-import'));
do $bw$
declare snapshot_id bigint; restaurant_id bigint; matches bigint[];
begin
 select id into snapshot_id from public.bevstats_reports where as_of_date='2026-11-02';
 if snapshot_id is null then raise exception 'Load the November 2 report before adding this row.'; end if;
 select array_agg(id) into matches from public.bevstats_locations
 where lower(regexp_replace(trim(name),'\s+',' ','g'))='b&w burgers buns & brews';
 if cardinality(matches)>1 then raise exception 'Multiple B&W locations matched. Nothing was changed.'; end if;
 if cardinality(matches)=1 then restaurant_id:=matches[1];
 else
  insert into public.bevstats_locations(name,address)
  values('B&W Burgers Buns & Brews','113 S. Peachtree St., Norcross, GA 30071') returning id into restaurant_id;
 end if;
 insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent)
 values(snapshot_id,restaurant_id,0,0,0,0)
 on conflict(report_id,location_id) do update set prior_beers=0,current_beers=0,reported_change_beers=0,reported_percent=0;
 insert into public.bevstats_baselines(location_id,source_report_id,baseline_start,baseline_end,baseline_beers,updated_as_of)
 values(restaurant_id,snapshot_id,'2026-10-01','2026-10-31',0,'2026-11-02')
 on conflict(location_id) do update set source_report_id=excluded.source_report_id,
 baseline_start=excluded.baseline_start,baseline_end=excluded.baseline_end,
 baseline_beers=0,updated_as_of=excluded.updated_as_of
 where public.bevstats_baselines.updated_as_of is null or public.bevstats_baselines.updated_as_of<=excluded.updated_as_of;
end $bw$;
commit;
select name,baseline_beers,current_beers,baseline_change_beers,baseline_percent
from public.bevstats_dashboard where name='B&W Burgers Buns & Brews'
and report_id=(select id from public.bevstats_reports where as_of_date='2026-11-02');
