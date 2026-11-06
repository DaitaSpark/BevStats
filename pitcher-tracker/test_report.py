"""Verify exact source values and safe initial report SQL generation."""
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build_static

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare_import', ROOT / 'supabase' / 'prepare_import.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class RealReportTests(unittest.TestCase):
    def test_exact_restaurant_rows_and_source_rounding(self):
        rows = json.loads((ROOT / 'supabase' / 'first-report.json').read_text())
        self.assertEqual(len(rows), 22)
        self.assertEqual(len({(r['name'], r['address']) for r in rows}),22)
        self.assertFalse(any(r['name'] == 'Bud Light' for r in rows))
        modern = next(r for r in rows if r['name'] == 'Modern Sports Restaurant')
        self.assertEqual(Decimal(modern['reported_change']), Decimal('-13.78'))
        self.assertEqual(Decimal(modern['current_case_equivalents'])-Decimal(modern['prior_case_equivalents']),Decimal('-13.77'))
        rocco = next(r for r in rows if r['name'] == "Rocco's Pub")
        self.assertEqual(rocco['current_case_equivalents'],'41.33')
        self.assertEqual(rocco['reported_change'],'0.00')
        secrets = next(r for r in rows if r['name'] == 'Secrets')
        self.assertEqual(secrets['reported_percent'],'100.00')

    def test_confirmed_import_is_atomic_and_deduplicates(self):
        sql = importer.generate('2025-10-01','2025-10-29','2026-10-01','2026-10-29')
        self.assertEqual(sql, (ROOT / 'supabase' / 'initial-import.sql').read_text())
        self.assertTrue(sql.startswith('begin;'))
        self.assertTrue(sql.endswith('commit;\n'))
        self.assertEqual(sql.count('insert into public.bevstats_report_totals'),22)
        self.assertEqual(sql.count('on conflict(report_id,location_id) do update'),22)
        self.assertIn("Rocco''s Pub",sql)
        self.assertNotIn('delete from',sql.lower())
        with self.assertRaises(ValueError):
            importer.generate('2025-10-29','2025-10-01','2026-10-01','2026-10-29')

    def test_import_converts_volumes_to_stored_beers_only(self):
        sql = importer.generate('2025-10-01','2025-10-29','2026-10-01','2026-10-29')
        self.assertIn('prior_beers,current_beers,reported_change_beers,reported_percent', sql)
        # Wild Wing: prior 55.11, current 62.00, change 6.89; percent stays 12.50.
        self.assertIn(',1322.64,1488.00,165.36,12.50)', sql)
        # Preserve the source's rounded change rather than recomputing it.
        self.assertIn(',991.92,661.44,-330.72,-33.33)', sql)
        self.assertNotIn('current_case_equivalents=', sql)

    def test_november_restaurant_import_and_missing_locations(self):
        spec = importlib.util.spec_from_file_location('november_import', ROOT/'supabase'/'prepare_november_import.py')
        module=importlib.util.module_from_spec(spec)
        import sys
        with patch.dict(sys.modules, {'prepare_import':importer}):
            spec.loader.exec_module(module)
            sql=module.build()
        data=json.loads((ROOT/'supabase'/'november-2026-report.json').read_text())
        rows=data['rows']
        self.assertEqual(len(rows),16)
        self.assertEqual(sum(Decimal(r['current_case_equivalents']) for r in rows),Decimal('27.56'))
        self.assertEqual(sum(Decimal(r['current_case_equivalents'])*24 for r in rows),Decimal('661.44'))
        self.assertEqual(sum(Decimal(r['current_case_equivalents'])==0 for r in rows),12)
        original=json.loads((ROOT/'supabase'/'first-report.json').read_text())
        old={(r['name'],r['address']) for r in original}
        new={(r['name'],r['address']) for r in rows}
        self.assertEqual(len(new-old),1)
        self.assertEqual(len(old-new),7)
        self.assertEqual(next(iter(new-old))[0], "Dave & Buster's - Sugarloaf")
        self.assertEqual(data['current_end'],'2026-11-07')
        self.assertNotIn('Bud Light',sql)
        self.assertNotIn('update public.bevstats_baselines',sql.lower())
        self.assertIn('select r.id,l.id,null,null,null,null',sql)
        self.assertIn('on conflict(report_id,location_id) do nothing',sql)
        self.assertEqual(sql,(ROOT/'supabase'/'import-november-2026.sql').read_text())

    def test_clean_october_reload_starts_november_awaiting(self):
        spec=importlib.util.spec_from_file_location('baseline_reload',ROOT/'supabase'/'prepare_baseline_reload.py')
        module=importlib.util.module_from_spec(spec)
        import sys
        with patch.dict(sys.modules,{'prepare_import':importer}):
            spec.loader.exec_module(module)
            sql=module.build()
        self.assertEqual(sql,(ROOT/'supabase'/'reload-october-baseline.sql').read_text())
        self.assertEqual(sql.count('begin;\n'),1)
        self.assertEqual(sql.count('\ncommit;'),1)
        self.assertEqual(sql.count('insert into public.bevstats_locations(name,address)'),22)
        self.assertIn('truncate table public.bevstats_baselines,public.bevstats_report_totals',sql)
        self.assertIn('select r.id,b.location_id,b.baseline_beers,null,null,null',sql)
        self.assertNotIn('2026-11-07',sql)
        self.assertNotIn("Sugarloaf",sql)
        self.assertNotIn('truncate table auth.',sql)
        rows=json.loads((ROOT/'supabase'/'first-report.json').read_text())
        total=sum(Decimal(r['current_case_equivalents']) for r in rows)
        self.assertEqual(total,Decimal('502.93'))
        self.assertEqual(total*24,Decimal('12070.32'))

    def test_corrected_empty_database_load(self):
        spec=importlib.util.spec_from_file_location('corrected_load',ROOT/'supabase'/'prepare_corrected_load.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        sql=module.build()
        self.assertEqual(sql,(ROOT/'supabase'/'load-october-november-2026.sql').read_text())
        self.assertIn("'2026-10-01','2026-10-07','2026-11-01','2026-11-07'",sql)
        self.assertIn('rec.october_ce*24,rec.november_ce*24,rec.change_ce*24,rec.percent_change',sql)
        self.assertIn("loaded_location_id,loaded_report_id,'2026-10-01','2026-10-07',rec.october_ce*24",sql)
        self.assertNotIn('corrected_report_source',sql)
        self.assertNotIn('create temporary table',sql.lower())
        self.assertNotIn('2026-10-29',sql)
        self.assertNotIn('2025-',sql)
        self.assertIn('truncate table public.bevstats_baselines,public.bevstats_report_totals',sql.lower())
        self.assertNotIn('truncate table auth.',sql.lower())
        self.assertNotIn('Sugarloaf missing',sql)
        self.assertIn("Dave & Buster''s - Sugarloaf",sql)
        self.assertNotIn('Alpharetta',sql)
        self.assertIn('t.current_beers>0 then 100::numeric',sql)
        rows=json.loads((ROOT/'supabase'/'november-2026-report.json').read_text())['rows']
        self.assertEqual(sum(Decimal(r['prior_case_equivalents']) for r in rows),Decimal('186.03'))
        self.assertEqual(sum(Decimal(r['current_case_equivalents']) for r in rows),Decimal('27.56'))

    def test_daily_november_second_source_and_safe_snapshot(self):
        spec=importlib.util.spec_from_file_location('daily_import',ROOT/'supabase'/'prepare_daily_import.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=json.loads((ROOT/'supabase'/'november-02-2026-report.json').read_text())
        sql=module.build(source)
        self.assertEqual(sql,(ROOT/'supabase'/'import-november-02-2026.sql').read_text())
        rows=source['rows']
        self.assertEqual(len(rows),22)
        self.assertEqual(sum(Decimal(r['november_ce']) for r in rows),Decimal('62.01'))
        self.assertEqual(sum(Decimal(r['october_ce']) for r in rows),Decimal('592.47'))
        self.assertEqual(sum(Decimal(r['november_ce'])==0 for r in rows),15)
        self.assertEqual(Decimal('62.01')*24,Decimal('1488.24'))
        self.assertTrue(all(r['address'] for r in rows))
        bw=next(r for r in rows if r['name']=='B&W Burgers Buns & Brews')
        self.assertTrue(all(Decimal(bw[k])==0 for k in ('october_ce','november_ce','change_ce','percent_change')))
        self.assertEqual(bw['address'],'113 S. Peachtree St., Norcross, GA 30071')
        self.assertNotIn('truncate',sql.lower())
        self.assertNotIn('delete from',sql.lower())
        self.assertIn('on conflict(as_of_date)',sql)
        self.assertIn('where report_id=snapshot_id',sql)
        self.assertIn('excluded.updated_as_of>=public.bevstats_baselines.updated_as_of',sql)
        from copy import deepcopy
        future=deepcopy(source);future.pop('replace_october_baseline')
        future_sql=module.build(future)
        self.assertNotIn('baseline_beers=excluded.baseline_beers',future_sql)
        self.assertNotIn('insert into public.bevstats_baselines',future_sql.lower())
        self.assertIn('Ambiguous restaurant name',sql)
        from copy import deepcopy
        invalid=deepcopy(source);invalid['period_confirmation_pending']=True
        with self.assertRaises(ValueError):module.build(invalid)
        invalid=deepcopy(source);invalid['rows'].append(deepcopy(invalid['rows'][0]))
        with self.assertRaises(ValueError):module.build(invalid)

    def test_november_third_replaces_cumulative_without_touching_october(self):
        spec=importlib.util.spec_from_file_location('daily_import',ROOT/'supabase'/'prepare_daily_import.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=json.loads((ROOT/'supabase'/'november-03-2026-report.json').read_text())
        sql=module.build(source)
        self.assertEqual(sql,(ROOT/'supabase'/'import-november-03-2026.sql').read_text())
        self.assertEqual(source['as_of_date'],'2026-11-03')
        self.assertEqual(source['current_end'],'2026-11-03')
        self.assertFalse(source['replace_october_baseline'])
        self.assertEqual(len(source['rows']),22)
        self.assertEqual(sum(Decimal(r['november_ce']) for r in source['rows']),Decimal('62.01'))
        for verb in ('insert into','update','delete from','alter table'):
            self.assertNotIn(verb+' public.bevstats_baselines',sql.lower())
        self.assertNotIn('truncate',sql.lower())
        self.assertNotIn('current_beers=current_beers+',sql.lower())
        self.assertIn('current_beers=excluded.current_beers',sql)
        self.assertIn("'2026-11-03'",sql)
        self.assertEqual(source['carried_forward_rows'][0]['name'],'B&W Burgers Buns & Brews')

    def test_november_fourth_cumulative_import(self):
        spec=importlib.util.spec_from_file_location('daily_import',ROOT/'supabase'/'prepare_daily_import.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=json.loads((ROOT/'supabase'/'november-04-2026-report.json').read_text())
        previous=json.loads((ROOT/'supabase'/'november-03-2026-report.json').read_text())
        sql=module.build(source)
        self.assertEqual(sql,(ROOT/'supabase'/'import-november-04-2026.sql').read_text())
        self.assertEqual(source['as_of_date'],'2026-11-04')
        self.assertEqual(source['current_end'],'2026-11-04')
        self.assertFalse(source['replace_october_baseline'])
        rows={r['name']:r for r in source['rows']}
        self.assertEqual(len(rows),22)
        self.assertEqual(sum(Decimal(r['november_ce']) for r in rows.values()),Decimal('144.68'))
        self.assertEqual(sum(Decimal(r['november_ce'])*24 for r in rows.values()),Decimal('3472.32'))
        self.assertEqual(rows['Wild Wing Cafe - Hamilton Mill']['november_ce'],'41.33')
        self.assertEqual(rows["Dillon's"]['november_ce'],'20.67')
        self.assertEqual(rows['The Oyster Pub - Dalton']['change_ce'],'-20.67')
        self.assertEqual(rows['Modern Sports Restaurant']['november_ce'],'6.89')
        self.assertEqual(rows['Local 7']['november_ce'],'6.89')
        self.assertEqual(rows['B&W Burgers Buns & Brews']['november_ce'],'0.00')
        self.assertTrue(all(r['october_ce']==rows[r['name']]['october_ce'] for r in previous['rows']))
        for verb in ('insert into','update','delete from','alter table'):
            self.assertNotIn(verb+' public.bevstats_baselines',sql.lower())
        self.assertIn('current_beers=excluded.current_beers',sql)
        self.assertNotIn('truncate',sql.lower())

    def test_build_rejects_secret_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict('os.environ',{'SUPABASE_URL':'https://example.supabase.co','SUPABASE_PUBLISHABLE_KEY':'sb_secret_bad'}):
                with self.assertRaises(ValueError):
                    build_static.build(tmp)


if __name__ == '__main__':
    unittest.main()
