"""Generate a standalone load of the corrected 16-restaurant October/November report."""
import json
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def literal(value):
    return "'"+str(value).replace("'","''")+"'"

def build():
    data=json.loads((ROOT/'november-2026-report.json').read_text(encoding='utf-8'))
    rows=data['rows']
    if len(rows)!=16 or len({(r['name'],r['address']) for r in rows})!=16:
        raise ValueError('Expected 16 unique restaurant rows')
    values=[]
    for row in rows:
        if row['name'].strip().lower() in ('total','bud light'):
            raise ValueError('Only restaurant rows may be loaded')
        nums=[Decimal(row[k]) for k in ('prior_case_equivalents','current_case_equivalents','reported_change','reported_percent')]
        if any(not n.is_finite() for n in nums) or min(nums[:2])<0:
            raise ValueError('Invalid quantities')
        values.append('('+','.join([literal(row['name']),literal(row['address']),*map(str,nums)])+')')
    migration=(ROOT/'set-october-2026-baseline.sql').read_text(encoding='utf-8')
    definition=migration[migration.index('create table if not exists'):migration.index('do $$')]
    view=migration[migration.index('create or replace view'):migration.index('notify pgrst')]
    # The report explicitly uses +100% for growth from zero; retain that convention.
    view=view.replace('when b.baseline_beers=0 and t.current_beers=0 then 0::numeric else null::numeric end', 'when b.baseline_beers=0 and t.current_beers=0 then 0::numeric\n      when b.baseline_beers=0 and t.current_beers>0 then 100::numeric else null::numeric end')
    return '''-- CORRECTED LOAD: October 1-7, 2026 baseline; November 1-7, 2026 actual data.
-- Excludes Total and Bud Light rows. CE volumes are converted to Beers once.
-- Requires the existing tables/Beers columns and enable-table-editing.sql.
-- Replaces ALL restaurant/report/baseline data. Keeps Auth accounts and editor permissions.
begin;
'''+definition+'''truncate table public.bevstats_baselines,public.bevstats_report_totals,
 public.bevstats_reports,public.bevstats_locations restart identity;
do $load$
declare rec record; loaded_report_id bigint; loaded_location_id bigint;
begin
 insert into public.bevstats_reports(prior_start,prior_end,current_start,current_end)
 values('2026-10-01','2026-10-07','2026-11-01','2026-11-07') returning id into loaded_report_id;
 for rec in select * from (values
'''+',\n'.join(values)+'''
 ) as source(name,address,october_ce,november_ce,change_ce,percent_change)
 loop
  insert into public.bevstats_locations(name,address)
  values(rec.name,rec.address) returning id into loaded_location_id;
  insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent)
  values(loaded_report_id,loaded_location_id,rec.october_ce*24,rec.november_ce*24,rec.change_ce*24,rec.percent_change);
  insert into public.bevstats_baselines(location_id,source_report_id,baseline_start,baseline_end,baseline_beers)
  values(loaded_location_id,loaded_report_id,'2026-10-01','2026-10-07',rec.october_ce*24);
 end loop;
end $load$;
'''+view+'''
grant select on public.bevstats_dashboard to anon,authenticated;
notify pgrst,'reload schema';
commit;
select count(*) as restaurants,count(current_beers) as november_entries,
 sum(baseline_beers) as october_baseline_beers,sum(baseline_beers)/24 as october_baseline_ce,
 sum(current_beers) as november_beers,sum(current_beers)/24 as november_ce
from public.bevstats_dashboard;
'''

if __name__=='__main__':
    (ROOT/'load-october-november-2026.sql').write_text(build(),encoding='utf-8')
    print('Created load-october-november-2026.sql. No live database changes made.')
