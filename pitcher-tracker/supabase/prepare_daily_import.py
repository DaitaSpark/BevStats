"""Generate a repeatable daily snapshot import without deleting report history."""
import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def literal(value):
    return "'"+str(value).replace("'","''")+"'"


def build(source):
    if source.get('period_confirmation_pending') is not False:
        raise ValueError('Confirm reporting periods before generating SQL')
    keys=('prior_start','prior_end','current_start','current_end','as_of_date')
    dates={key:date.fromisoformat(source[key]) for key in keys}
    if not dates['prior_start']<=dates['prior_end']<dates['current_start']<=dates['current_end']<=dates['as_of_date']:
        raise ValueError('Invalid report dates')
    if dates['current_start'].day!=1:
        raise ValueError('Daily imports must contain month-to-date totals')
    rows=source['rows']
    if not rows or len(rows)>1000: raise ValueError('Use 1-1000 restaurants')
    seen=set();values=[]
    for r in rows:
        name=' '.join(r['name'].split())
        if name.casefold() in ('total','bud light') or name.casefold().startswith('bud light '):
            raise ValueError('Only restaurant rows are allowed')
        if not name or len(name)>200 or not isinstance(r['address'],str) or not r['address'].strip():
            raise ValueError('Restaurant name and known address are required')
        identity=name.casefold()
        if identity in seen:raise ValueError('Duplicate restaurant name needs manual matching')
        seen.add(identity)
        numbers=[Decimal(r[k]) for k in ('october_ce','november_ce','change_ce','percent_change')]
        if any(not n.is_finite() or n!=n.quantize(Decimal('.01')) for n in numbers) or min(numbers[:2])<0:
            raise ValueError('Invalid report numbers')
        values.append('('+','.join([literal(name),literal(r['address']),*map(str,numbers)])+')')
    baseline_statement='-- Existing October baselines are preserved; no baseline rows are written.'
    baseline_schema=''
    baseline_note='October baseline is fixed. This import does not write the baseline table.'
    if source.get('replace_october_baseline') is True:
        baseline_note='October baseline replacement is explicitly authorized for this correction.'
        baseline_schema='alter table public.bevstats_baselines add column if not exists updated_as_of date;'
        baseline_statement=f'''insert into public.bevstats_baselines(location_id,source_report_id,baseline_start,baseline_end,baseline_beers,updated_as_of)
  values(restaurant_id,snapshot_id,{literal(dates['prior_start'])},{literal(dates['prior_end'])},rec.october_ce*24,{literal(dates['as_of_date'])})
  on conflict(location_id) do update set source_report_id=excluded.source_report_id,
   baseline_start=excluded.baseline_start,baseline_end=excluded.baseline_end,
   baseline_beers=excluded.baseline_beers,updated_as_of=excluded.updated_as_of
  where public.bevstats_baselines.updated_as_of is null
    or excluded.updated_as_of>=public.bevstats_baselines.updated_as_of;'''
    ds={k:literal(v) for k,v in dates.items()}
    return f'''-- DAILY SNAPSHOT: {dates['as_of_date']}. Restaurant rows only; CE -> Beers x24.
-- Replaces only this day's snapshot on reimport. Other reports and location IDs are retained.
-- {baseline_note}
-- Future imports preserve existing baselines unless replace_october_baseline is explicitly enabled.
-- Requires existing Beers tables, baseline view and editor permissions.
begin;
select pg_advisory_xact_lock(hashtext('bevstats-daily-import'));
alter table public.bevstats_reports add column if not exists as_of_date date;
create unique index if not exists bevstats_reports_as_of_date_unique
 on public.bevstats_reports(as_of_date) where as_of_date is not null;
{baseline_schema}
do $daily$
declare rec record; snapshot_id bigint; restaurant_id bigint; matched_ids bigint[];
begin
 insert into public.bevstats_reports(prior_start,prior_end,current_start,current_end,as_of_date)
 values({ds['prior_start']},{ds['prior_end']},{ds['current_start']},{ds['current_end']},{ds['as_of_date']})
 on conflict(as_of_date) where as_of_date is not null do update
 set prior_start=excluded.prior_start,prior_end=excluded.prior_end,
 current_start=excluded.current_start,current_end=excluded.current_end,loaded_at=now()
 returning id into snapshot_id;
 -- Clearing this day's imported values makes omission in a corrected file mean awaiting.
 update public.bevstats_report_totals set prior_beers=null,current_beers=null,
  reported_change_beers=null,reported_percent=null where report_id=snapshot_id;
 for rec in select * from (values
'''+',\n'.join(values)+f'''
 ) as source(name,address,october_ce,november_ce,change_ce,percent_change) loop
  select array_agg(id) into matched_ids from public.bevstats_locations
   where lower(regexp_replace(trim(name),'\\s+',' ','g'))=lower(rec.name);
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
  {baseline_statement}
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
where r.as_of_date={ds['as_of_date']} group by r.as_of_date;
'''


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    a.output.write_text(build(json.loads(a.source.read_text(encoding='utf-8'))),encoding='utf-8')
    print('Generated daily import SQL. No database changes executed.')
