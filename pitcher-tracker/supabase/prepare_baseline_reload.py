"""Prepare a clean October baseline reload and an empty November period."""
from pathlib import Path
from prepare_import import generate

ROOT=Path(__file__).resolve().parent


def build():
    original=generate('2025-10-01','2025-10-29','2026-10-01','2026-10-29')
    assert original.startswith('begin;\n') and original.endswith('commit;\n')
    import_body=original[len('begin;\n'):-len('commit;\n')]
    migration=(ROOT/'set-october-2026-baseline.sql').read_text(encoding='utf-8')
    begin=migration.index('begin;\n')+len('begin;\n')
    end=migration.index('\ncommit;',begin)
    baseline_body=migration[begin:end]
    # The snapshot table may not have existed in an older deployment.
    create_end=baseline_body.index('\nalter table')
    create_baseline=baseline_body[:create_end]
    sql='''-- CLEAN RELOAD: replaces restaurant/report/baseline data with the 22 supplied restaurants.
-- Keeps Auth accounts, editor permissions, tables, views and functions.
-- November starts NULL/awaiting. Do NOT run the earlier November import after this.
begin;
'''+create_baseline+'''
truncate table public.bevstats_baselines,public.bevstats_report_totals,
 public.bevstats_reports,public.bevstats_locations restart identity;
'''+import_body+baseline_body+'''
commit;
select (select count(*) from public.bevstats_locations) as restaurants,
 (select count(*) from public.bevstats_baselines) as baseline_restaurants,
 (select sum(baseline_beers) from public.bevstats_baselines) as october_baseline_beers,
 (select sum(baseline_beers)/24 from public.bevstats_baselines) as october_baseline_ce,
 count(*) as november_restaurants,count(t.current_beers) as november_entries,
 count(*) filter(where t.current_beers is null) as awaiting_november
from public.bevstats_report_totals t join public.bevstats_reports r on r.id=t.report_id
where r.current_start='2026-11-01' and r.current_end='2026-11-01';
'''
    return sql


if __name__=='__main__':
    (ROOT/'reload-october-baseline.sql').write_text(build(),encoding='utf-8')
    print('Prepared reload-october-baseline.sql. No live database changes executed.')
