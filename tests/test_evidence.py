"""Contract and evidence tests. These do not assert that every scenario passes."""
import hashlib
import json
import unittest
from pathlib import Path
from dataclasses import asdict
import numpy as np
import pandas as pd
from src.model import FS, F0, Case, Control, simulate, harmonic_metrics
from src.study import main_cases, holdout_cases

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'

class ModelContract(unittest.TestCase):
    def test_configuration_matches_implemented_metric(self):
        cfg=json.loads((ROOT/'study_config.json').read_text())
        self.assertEqual(cfg['fs_control_hz'],FS)
        self.assertEqual(cfg['f_grid_hz'],F0)
        self.assertEqual(cfg['measurement_cycles'],10)
        self.assertEqual(cfg['thd_harmonics'],[2,40])
        self.assertEqual(cfg['thd_limit_pct'],5.)
    def test_matrix_size_and_zero_exclusion(self):
        cases=main_cases()
        self.assertEqual(len(cases),72)
        self.assertEqual(len({(c.p,c.q,c.vrms) for c in cases}),72)
        self.assertTrue(all(c.p!=0 or c.q!=0 for c in cases))
    def test_holdout_reproducible(self):
        a=[asdict(x) for x in holdout_cases()];b=[asdict(x) for x in holdout_cases()]
        self.assertEqual(a,b);self.assertEqual(len(a),72)
    def test_zero_command_rejected(self):
        with self.assertRaises(ValueError):simulate(Case('bad',p=0,q=0),Control())
    def test_bad_inductance_rejected(self):
        with self.assertRaises(ValueError):simulate(Case('bad',lf=-1),Control())
    def test_known_signal(self):
        t=np.arange(6400)/FS
        w=np.zeros((6400,9));w[:,0]=t;w[:,1]=230*np.sqrt(2)*np.sin(2*np.pi*F0*t)
        w[:,2]=np.sqrt(2)*(10*np.sin(2*np.pi*F0*t)+.5*np.sin(3*2*np.pi*F0*t))
        m,_=harmonic_metrics(w,2300,0,230)
        self.assertAlmostEqual(m['thd_pct'],5,places=10)

class ExecutedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df=pd.read_csv(R/'all_runs.csv');cls.summary=json.loads((R/'summary.json').read_text())
    def test_count_and_unique_runs(self):
        self.assertEqual(len(self.df),591)
        self.assertEqual(self.df.run_id.nunique(),591)
    def test_numeric_columns_finite(self):
        cols=self.df.select_dtypes(include='number').columns.difference(['step_settling_s','step_peak_a'])
        self.assertTrue(np.isfinite(self.df[cols].to_numpy()).all())
    def test_threshold_decisions(self):
        np.testing.assert_array_equal(self.df.thd_pass,self.df.thd_pct<=5.)
        np.testing.assert_array_equal(self.df.combined_pass,self.df.thd_pass & self.df.guardrail_pass)
    def test_summary_consistent(self):
        for phase in ['baseline','improved','holdout_baseline','holdout_improved']:
            d=self.df[self.df.phase==phase];s=self.summary[phase]
            self.assertEqual(len(d),s['n']);self.assertEqual(int(d.thd_pass.sum()),s['thd_pass'])
            self.assertEqual(int(d.combined_pass.sum()),s['combined_pass'])
            self.assertAlmostEqual(d.thd_pct.mean(),s['mean_thd_pct'],places=9)
    def test_comparison_inputs_unchanged(self):
        cols=list(Case.__dataclass_fields__)
        for a,b in [('baseline','improved'),('holdout_baseline','holdout_improved')]:
            x=self.df[self.df.phase==a][cols].reset_index(drop=True)
            y=self.df[self.df.phase==b][cols].reset_index(drop=True)
            pd.testing.assert_frame_equal(x,y)
    def test_selected_control_frozen(self):
        selection=json.loads((R/'selected_control.json').read_text())
        self.assertEqual(selection['model_sha256'],hashlib.sha256((ROOT/'src/model.py').read_bytes()).hexdigest())
        self.assertEqual(selection['config_sha256'],hashlib.sha256((ROOT/'study_config.json').read_bytes()).hexdigest())
        for key,val in selection['control'].items():
            np.testing.assert_allclose(self.df[self.df.phase.isin(['improved','holdout_improved'])][key],val,atol=0,rtol=0)
        self.assertEqual(len(selection['training_case_ids']),9)
        log=json.loads((R/'stage_log.json').read_text());freeze=next(x for x in log if x['stage']=='Analyze/Freeze')
        self.assertIn(hashlib.sha256((R/'selected_control.json').read_bytes()).hexdigest(),freeze['detail'])
    def test_failures_not_removed(self):
        h=self.df[self.df.phase=='holdout_improved'];f=pd.read_csv(R/'holdout_failures.csv')
        self.assertEqual(set(f.case_id),set(h.loc[~h.combined_pass,'case_id']))
        self.assertEqual(len(f),7)
        self.assertTrue(bool(h[h.case_id=='H037'].iloc[0].thd_pass))
        self.assertFalse(bool(h[h.case_id=='H037'].iloc[0].guardrail_pass))
    def test_raw_harmonics_reproduce_all_runs(self):
        maxerror=0.
        for archive,frame in self.df.groupby('wave_archive'):
            with np.load(ROOT/archive,allow_pickle=False) as traces:
                for row in frame.itertuples():
                    a=traces[row.run_id]
                    x=a[2,-6400:] if row.wave_full else a[0]
                    self.assertEqual(len(x),6400)
                    rms=np.sqrt(2)*np.abs(np.fft.rfft(x)[np.arange(1,41)*10])/6400
                    calc=100*np.linalg.norm(rms[1:])/rms[0]
                    maxerror=max(maxerror,abs(calc-row.thd_pct))
                    np.testing.assert_allclose(rms,[getattr(row,f'h{k:02d}_rms_a') for k in range(1,41)],rtol=1e-11,atol=1e-11)
        self.assertLess(maxerror,1e-9)
    def test_verification_gate(self):
        v=json.loads((R/'verification.json').read_text())
        self.assertEqual(len(v['checks']),23);self.assertTrue(v['all_passed'])
        self.assertTrue(all(c['value']<=c['limit'] and c['passed'] for c in v['checks']))
    def test_factor_decomposition(self):
        f=pd.read_csv(R/'factor_effects.csv')
        self.assertAlmostEqual(f.share_pct.sum(),100,places=8)
        self.assertNotIn('p_value',f.columns)
    def test_report_boundaries(self):
        text=(ROOT/'report/index.html').read_text()
        for phrase in ['실제 제품 및 사내 BB 완료는 미입증','H037','T1','empirical validation','독립 MBB']:
            self.assertIn(phrase,text)
        self.assertNotIn('<script src=',text)
        self.assertNotIn('cdn.',text)
    def test_anonymized_comparison_complete(self):
        cases=json.loads((ROOT/'docs/reference_cases.json').read_text())
        self.assertEqual(len(cases),11);self.assertEqual(sum(c['slides'] for c in cases),230)
        self.assertEqual(len({c['id'] for c in cases}),11)
    def test_manifest_hashes(self):
        manifest=json.loads((R/'manifest.json').read_text())
        for entry in manifest['files']:
            p=ROOT/entry['path'];self.assertEqual(p.stat().st_size,entry['bytes'])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),entry['sha256'],entry['path'])
    def test_no_corporate_pptx_copied(self):
        self.assertEqual(list(ROOT.rglob('*.pptx')),[])

if __name__=='__main__': unittest.main()
