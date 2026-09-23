import unittest, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from src.model import Case, Control, simulate, metrics, FS, W0
from src.audit import audit
ROOT=Path(__file__).resolve().parents[1]

class StudyChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=ROOT/'results'; cls.df=pd.read_csv(cls.r/'all_runs.csv')
        cls.summary=json.loads((cls.r/'summary.json').read_text())
        cls.audit=audit(ROOT)
    def test_01_unique_run_identifiers(self): self.assertTrue(self.df.run_id.is_unique)
    def test_02_all_raw_values_recomputed(self): self.assertTrue(all(x['passed'] for x in self.audit))
    def test_03_expected_experiment_counts(self):
        sizes={'baseline':45,'improved':45,'doe':243,'sentinel_baseline':36,'sentinel_improved':36,'holdout_baseline':72,'holdout_improved':72,'ablation':54,'phase':28,'reverse_power':8,'transient':6,'refinement':4,'duration':2,'plant_sensitivity':12}
        self.assertEqual(self.df.groupby('group').size().to_dict(),sizes)
    def test_04_training_disjoint_from_main(self):
        t=pd.read_csv(self.r/'training_cases.csv'); m=pd.read_csv(self.r/'main_cases.csv')
        points=lambda f:set(map(tuple,f[['p','q','vrms']].round(8).to_numpy()))
        self.assertFalse(points(t)&points(m))
    def test_05_before_after_same_points(self):
        for a,b in [('baseline','improved'),('holdout_baseline','holdout_improved'),('sentinel_baseline','sentinel_improved')]:
            x=pd.read_csv(self.r/f'{a}.csv'); y=pd.read_csv(self.r/f'{b}.csv')
            pd.testing.assert_frame_equal(x[['case_id','p_ref','q_ref','vrms']],y[['case_id','p_ref','q_ref','vrms']])
    def test_06_control_has_no_plant_error_input(self):
        self.assertEqual(set(Control.__dataclass_fields__),{'design_hz','k3','k5','res_width_hz'})
    def test_07_selection_uses_training_aggregate(self):
        x=pd.read_csv(self.r/'doe_candidates.csv').iloc[0]
        c=self.summary['selected']
        self.assertEqual([x.ctl_design_hz,x.ctl_k3,x.ctl_k5],[c['design_hz'],c['k3'],c['k5']])
    def test_08_frozen_hashes(self):
        f=json.loads((self.r/'protocol_freeze.json').read_text())
        for p,h in f['source_sha256'].items(): self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
    def test_09_numerical_unit_checks(self):
        self.assertTrue(all(x['passed'] for x in json.loads((self.r/'verification.json').read_text())))
    def test_10_aggregate_from_all_points(self):
        for g in ['baseline','improved','holdout_baseline','holdout_improved','sentinel_baseline','sentinel_improved']:
            f=self.df[self.df.group==g]; s=self.summary[g]
            self.assertEqual(s['n'],len(f)); self.assertEqual(s['combined_pass'],int(f.combined_pass.sum()))
            self.assertAlmostEqual(s['mean_thd'],float(f.thd_pct.mean()),places=10)
    def test_11_no_hidden_failed_point_filter(self):
        x=pd.read_csv(self.r/'sentinel_failures.csv'); y=self.df[(self.df.group=='sentinel_improved')&(~self.df.combined_pass)]
        self.assertEqual(set(x.run_id),set(y.run_id))
    def test_12_source_window_shape(self):
        for p in (ROOT/'data').glob('*.npz'):
            with np.load(p,allow_pickle=False) as z:
                self.assertEqual(z['wave'].shape[1],25600 if p.stem=='transient' else 6400)
                self.assertEqual(z['wave'].shape[2],10)
    def test_13_data_safety(self):
        self.assertFalse(list(ROOT.rglob('*.pptx'))); self.assertFalse(list(ROOT.rglob('*.pdf')))
    def test_14_zero_current_rejected(self):
        with self.assertRaises(ValueError): simulate(Case('bad',p=0,q=0))
    def test_15_nonphysical_parameter_rejected(self):
        with self.assertRaises(ValueError): simulate(Case('bad',lf=-1))
    def test_16_current_envelope_rejected(self):
        with self.assertRaises(ValueError): simulate(Case('bad',p=10000))
    def test_17_deterministic_same_input(self):
        c=Case('repeat',p=700); a=simulate(c,cycles=20); b=simulate(c,cycles=20)
        np.testing.assert_array_equal(a,b)
    def test_18_public_reference_metadata(self):
        e=json.loads((ROOT/'evidence/public_references.json').read_text())
        self.assertEqual(len(e),5); self.assertTrue(all(x['url'].startswith('https://') for x in e))
    def test_19_guard_joint_logic(self):
        self.assertTrue(np.array_equal(self.df.combined_pass,self.df.thd_pass & self.df.guard_pass))
    def test_20_reference_comparison_coverage(self):
        e=json.loads((ROOT/'docs/reference_cases.json').read_text())
        self.assertEqual(len(e),11); self.assertEqual(sum(x['slides'] for x in e),230)

if __name__=='__main__': unittest.main()
