-- DAILY SNAPSHOT: 2026-11-05. Restaurant rows only; CE -> Beers x24.
-- Replaces only this day's snapshot on reimport. Other reports and location IDs are retained.
-- October baseline is fixed. This import does not write the baseline table.
-- Future imports preserve existing baselines unless replace_october_baseline is explicitly enabled.
-- Requires existing Beers tables, baseline view and editor permissions.
begin;
select pg_advisory_xact_lock(hashtext('bevstats-daily-import'));
alter table public.bevstats_reports add column if not exists as_of_date date;
create unique index if not exists bevstats_reports_as_of_date_unique
 on public.bevstats_reports(as_of_date) where as_of_date is not null;

do $daily$
declare rec record; snapshot_id bigint; restaurant_id bigint; matched_ids bigint[];
begin
 insert into public.bevstats_reports(prior_start,prior_end,current_start,current_end,as_of_date)
 values('2026-10-01','2026-10-31','2026-11-01','2026-11-05','2026-11-05')
 on conflict(as_of_date) where as_of_date is not null do update
 set prior_start=excluded.prior_start,prior_end=excluded.prior_end,
 current_start=excluded.current_start,current_end=excluded.current_end,loaded_at=now()
 returning id into snapshot_id;
 -- Clearing this day's imported values makes omission in a corrected file mean awaiting.
 update public.bevstats_report_totals set prior_beers=null,current_beers=null,
  reported_change_beers=null,reported_percent=null where report_id=snapshot_id;
 for rec in select * from (values
('Wild Wing Cafe - Hamilton Mill','3517 Braselton Highway, Dacula, GA 30019',62.00,41.33,-20.67,-33.33),
('Hammerheads Seafood & Sports','415 Peachtree Indus Blvd, Suwanee, GA 30024',27.56,20.67,-6.89,-25.00),
('Dillon''s','850 Dogwood Rd., Lawrenceville, GA 30044',62.00,20.67,-41.33,-66.67),
('The Oyster Pub - Dalton','933 MARKET ST, Dalton, GA 30720',34.44,13.78,-20.67,-60.00),
('The Bat And Ball Pub','2150-B Johnson Ferry Rd, Atlanta, GA 30319',20.67,6.89,-13.78,-66.67),
('Sidelines Grille Jasper','800 Noah drive, Jasper, GA 30143',20.67,6.89,-13.78,-66.67),
('Secrets','3962 Lawrenceville Hwy, Tucker, GA 30084',13.78,6.89,-6.89,-50.00),
('Modern Sports Restaurant','203 S Tennessee St, Cartersville, GA 30120',34.44,6.89,-27.56,-80.00),
('Mazzy''s Sports Bar & Grill - Duluth','3855 Venture Drive, Duluth, GA 30096',20.67,6.89,-13.78,-66.67),
('Local 7','2316 Main Street, Tucker, GA 30084',34.44,6.89,-27.56,-80.00),
('Big Shots Billiards','101 Emma Lane, Woodstock, GA 30189',6.89,6.89,0.00,0.00),
('Will Henry''s','1228 Rockbridge Rd., Stone Mountain, GA 30087',27.56,0.00,-27.56,-100.00),
('Tony''s Sports Bar & Grill - Duluth','2590 PEACHTREE INDUSTRIAL BLVD, Duluth, GA 30096',27.56,0.00,-27.56,-100.00),
('Rocco''s Pub','47 Mountainside Village, Jasper, GA 30143',55.11,0.00,-55.11,-100.00),
('Johnny''s Pizza - Hickory Flat','6124 Hickory Flat Highway, Canton, GA 30115',20.67,0.00,-20.67,-100.00),
('Jimmy''s Tequila & Carnes Mexican Steak Seafood','6365 Peachtree Industrial Blvd, Doraville, GA 30360',27.56,0.00,-27.56,-100.00),
('Jefferson''s - Dalton','200 North Hamilton St, Dalton, GA 30720',6.89,0.00,-6.89,-100.00),
('Hooligans','8440 Holcomb Bridge Rd, Roswell, GA 30022',13.78,0.00,-13.78,-100.00),
('Firebird Restaurant','4719 Ashford Dunwoody Rd, Dunwoody, GA 30338',27.56,0.00,-27.56,-100.00),
('El Dorado - Cartersville','910 Joe Frank Harris Pkwy Se, Cartersville, GA 30120',6.89,0.00,-6.89,-100.00),
('Dave & Buster''s - Sugarloaf','5900 Sugarloaf Pkwy, Lawrenceville, GA 30043',41.33,0.00,-41.33,-100.00)
 ) as source(name,address,october_ce,november_ce,change_ce,percent_change) loop
  select array_agg(id) into matched_ids from public.bevstats_locations
   where lower(regexp_replace(trim(name),'\s+',' ','g'))=lower(rec.name);
  if cardinality(matched_ids)>1 then raise exception 'Ambiguous restaurant name: %',rec.name; end if;
  if cardinality(matched_ids)=1 then
   restaurant_id:=matched_ids[1];
  else
   insert into public.bevstats_locations(name,address) values(rec.name,rec.address)
   returning id into restaurant_id;
  end if;
  insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent)
  values(snapshot_id,restaurant_id,rec.october_ce*24,rec.november_ce*24,rec.change_ce*24,rec.percent_change)
  on conflict(report_id,location_id) do update set prior_beers=excluded.prior_beers,
   current_beers=excluded.current_beers,reported_change_beers=excluded.reported_change_beers,
   reported_percent=excluded.reported_percent;
  -- Existing October baselines are preserved; no baseline rows are written.
 end loop;
 -- Missing restaurants are not assumed to have zero sales.
 insert into public.bevstats_report_totals(report_id,location_id)
 select snapshot_id,id from public.bevstats_locations on conflict(report_id,location_id) do nothing;
end $daily$;
notify pgrst,'reload schema';
commit;
select r.as_of_date,count(*) as restaurants,count(t.current_beers) as reported_restaurants,
 count(*) filter(where t.current_beers is null) as awaiting_restaurants,
 sum(t.prior_beers)/24 as source_october_ce,sum(t.current_beers)/24 as november_ce,
 sum(t.current_beers) as november_beers
from public.bevstats_report_totals t join public.bevstats_reports r on r.id=t.report_id
where r.as_of_date='2026-11-05' group by r.as_of_date;
