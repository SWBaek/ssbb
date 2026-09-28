"""Specification gates and implementation checks; not hardware validation."""
from model import *
from dataclasses import replace
from scipy.integrate import solve_ivp
import unittest

class SpecTests(unittest.TestCase):
    def test_voltage(self):self.assertEqual(V_NOM,240.)
    def test_current(self):self.assertEqual(I_RATED,48.)
    def test_product_arithmetic(self):self.assertEqual(240*48,11520)
    def test_class_label_matches_arithmetic(self):self.assertEqual(SPEC['user_confirmed']['rated_apparent_power_va'],240*48)
    def test_peak_circle(self):self.assertAlmostEqual(I_PEAK_MAX,67.88225099390857)
    def test_pwm_period(self):self.assertEqual(TP,16e-6)
    def test_control_period(self):self.assertEqual(TS,16e-6)
    def test_equal_frequencies(self):self.assertEqual(FCTRL,FSW)
    def test_no_32us(self):self.assertNotEqual(TS,32e-6)
    def test_confirmed_schema(self):assert_spec()
    def test_d48_accepted(self):validate(Case('d48',I_PEAK_MAX,0))
    def test_q48_accepted(self):validate(Case('q48',0,I_PEAK_MAX))
    def test_double_fullscale_rejected(self):
        with self.assertRaises(ValueError):validate(Case('bad',I_PEAK_MAX,I_PEAK_MAX))
    def test_above_limit_rejected(self):
        with self.assertRaises(ValueError):validate(Case('bad',I_PEAK_MAX+.01,0))
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):validate(Case('bad',float('nan'),0))
    def test_wrong_step_rejected(self):
        with self.assertRaises(ValueError):simulate(Case('bad',10,0),Control(),dt_s=3e-6)
    def test_negative_deadtime_rejected(self):
        with self.assertRaises(ValueError):validate(Case('bad',10,0,dead_s=-1e-9))
    def test_axis_meaning(self):
        t=np.linspace(0,1/60,10001);th=2*np.pi*60*t;d=40.;q=30.;ia=d*np.cos(th)-q*np.sin(th);ib=d*np.sin(th)+q*np.cos(th)
        self.assertLess(np.max(abs(ia*np.cos(th)+ib*np.sin(th)-d)),1e-12)
        self.assertLess(np.max(abs(-ia*np.sin(th)+ib*np.cos(th)-q)),1e-12)
    def test_current_norm_rms(self):
        th=2*np.pi*np.arange(10000)/10000;i=40*np.cos(th)-30*np.sin(th)
        self.assertAlmostEqual(np.sqrt(np.mean(i*i)),50/SQ2)
    def test_q_power_sign(self):
        th=2*np.pi*np.arange(10000)/10000;i=40*np.cos(th)-30*np.sin(th);v=240*SQ2*np.cos(th)
        self.assertAlmostEqual(np.mean(v*i),240*40/SQ2)
        self.assertAlmostEqual(SQ2*240*np.mean(i*np.sin(th)),-240*30/SQ2)
    def test_fourier_known_signal(self):
        t=np.linspace(0,.25,125001);th=2*np.pi*60*t;isig=10*np.cos(th)+.3*np.cos(3*th)+.4*np.sin(5*th)
        h,_=harmonics_projection(t,isig,60,0);self.assertAlmostEqual(100*np.linalg.norm(h[1:])/h[0],5.,places=9)
    def test_60hz_harmonic_centers(self):self.assertEqual([3*F0,5*F0,7*F0],[180.,300.,420.])
    def test_sogi_poles_stable(self):
        ad,_,_=coefficients(Control());self.assertTrue(np.all(abs(np.linalg.eigvals(ad))<1))
    def test_resonator_poles_stable(self):
        for b in [4,8,16]:
            *_,h=coefficients(Control(kr_ohm=18,band_hz=b))
            for z in h:self.assertTrue(np.all(abs(np.roots([1,z[1],z[2]]))<1))
    def test_disabled_resonators(self):
        *_,h=coefficients(Control());self.assertTrue(np.all(h[:,0]==0))
    def test_rl_exact(self):
        i,z=rl_sensor(3,2,320,300,16e-6,.0011,.18,2*np.pi*10000,False,0,400)
        expected=20/.18+(3-20/.18)*np.exp(-.18/.0011*16e-6);self.assertAlmostEqual(i,expected,places=12)
    def test_sensor_against_independent_ode(self):
        a,b=rl_sensor(3,2,320,300,16e-6,.0011,.18,2*np.pi*10000,False,0,400)
        sol=solve_ivp(lambda t,y:[(20-.18*y[0])/.0011,2*np.pi*10000*(y[0]-y[1])],[0,16e-6],[3,2],rtol=1e-10,atol=1e-12)
        self.assertLess(np.max(abs(sol.y[:,-1]-[a,b])),1e-8)
    def test_diode_zero_clamp(self):
        i,z=rl_sensor(.1,.1,0,300,16e-6,.0011,.18,62831.,True,0,400);self.assertEqual(i,0.)

if __name__=='__main__':
    import io
    s=io.StringIO();r=unittest.TextTestRunner(stream=s,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SpecTests))
    (ROOT/'qa/unit_tests.log').write_text(s.getvalue())
    (ROOT/'qa/unit_tests.json').write_text(json.dumps({'tests_run':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'success':r.wasSuccessful()},indent=2))
    print(s.getvalue());raise SystemExit(0 if r.wasSuccessful() else 1)
