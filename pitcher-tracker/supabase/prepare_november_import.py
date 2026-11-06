"""Generate the provided November restaurant import; preserve the fixed October baseline."""
import json
from pathlib import Path
from prepare_import import generate, quote

ROOT=Path(__file__).resolve().parent


def build():
    report=json.loads((ROOT/'november-2026-report.json').read_text(encoding='utf-8'))
    dates=[report[k] for k in ('prior_start','prior_end','current_start','current_end')]
    sql=generate(*dates,rows=report['rows'])
    guard="""do $$ begin
 if to_regclass('public.bevstats_baselines') is null then
  raise exception 'Run set-october-2026-baseline.sql first.';
 end if;
 if not exists(select 1 from public.bevstats_baselines) then
  raise exception 'The October baseline has not been established.';
 end if;
end $$;
"""
    sql=sql.replace('begin;\n','begin;\n'+guard,1)
    predicate=' and '.join(f'r.{k}={quote(report[k])}' for k in ('prior_start','prior_end','current_start','current_end'))
    missing=f"""-- Unreported restaurants remain NULL (awaiting), never inferred as zero.
insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent)
select r.id,l.id,null,null,null,null from public.bevstats_locations l
cross join public.bevstats_reports r where {predicate}
on conflict(report_id,location_id) do nothing;
"""
    sql=sql.replace('commit;\n',missing+'commit;\n',1)
    sql+=f"""select count(*) as restaurants,count(t.current_beers) as reported_restaurants,
 count(*) filter(where t.current_beers is null) as awaiting_restaurants,
 sum(t.current_beers) as november_beers,sum(t.current_beers)/24 as november_ce
from public.bevstats_report_totals t join public.bevstats_reports r on r.id=t.report_id
where {predicate};
"""
    return sql


if __name__=='__main__':
    (ROOT/'import-november-2026.sql').write_text(build(),encoding='utf-8')
    print('Prepared import-november-2026.sql; no database changes executed.')
