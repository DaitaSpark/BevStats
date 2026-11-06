"""Generate an atomic, repeatable initial import after confirming report dates."""
import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def generate(prior_start, prior_end, current_start, current_end, rows=None):
    dates = [date.fromisoformat(d) for d in (prior_start, prior_end, current_start, current_end)]
    if dates[0] > dates[1] or dates[2] > dates[3]:
        raise ValueError('Report end dates must follow start dates')
    if rows is None:
        rows = json.loads((ROOT / 'first-report.json').read_text(encoding='utf-8'))
    seen = set()
    statements = ['begin;', 'insert into public.bevstats_reports(prior_start,prior_end,current_start,current_end) values (' + ','.join(map(quote, dates)) + ') on conflict do nothing;']
    report = '(select id from public.bevstats_reports where ' + ' and '.join(f'{k}={quote(v)}' for k,v in zip(('prior_start','prior_end','current_start','current_end'), dates)) + ')'
    for row in rows:
        identity = (row['name'], row['address'])
        if identity in seen or row['name'].strip().lower() == 'bud light':
            raise ValueError('Duplicate or brand-detail row')
        seen.add(identity)
        values = [Decimal(row[k]) for k in ('prior_case_equivalents','current_case_equivalents','reported_change','reported_percent')]
        if any(not n.is_finite() or n != n.quantize(Decimal('.01')) for n in values) or min(values[:2]) < 0:
            raise ValueError('Invalid report quantities')
        values[:3] = [n * 24 for n in values[:3]]
        name, address = map(quote, identity)
        statements.append(f'insert into public.bevstats_locations(name,address) values ({name},{address}) on conflict(name,address) do nothing;')
        location = f'(select id from public.bevstats_locations where name={name} and address={address})'
        statements.append('insert into public.bevstats_report_totals(report_id,location_id,prior_beers,current_beers,reported_change_beers,reported_percent) values (' + ','.join([report, location, *map(str,values)]) + ') on conflict(report_id,location_id) do update set prior_beers=excluded.prior_beers,current_beers=excluded.current_beers,reported_change_beers=excluded.reported_change_beers,reported_percent=excluded.reported_percent;')
    statements.append('commit;')
    return '\n'.join(statements) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('prior-start','prior-end','current-start','current-end'):
        parser.add_argument('--'+key, required=True, help='Confirmed report date: YYYY-MM-DD')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(generate(args.prior_start,args.prior_end,args.current_start,args.current_end),encoding='utf-8')
