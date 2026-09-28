"""Post-run comparison only. Reference metrics never enter simulation or selection."""
from model import ROOT
import json,math
r=json.loads((ROOT/'local_reference.json').read_text());s=json.loads((ROOT/'results/summary.json').read_text())
diffs={}
for key,val in r['metrics'].items():
    a=s
    for p in key.split('/'):a=a[p]
    if isinstance(val,(int,str,bool)):
        assert a==val,(key,a,val)
    else:
        diffs[key]=abs(a-val);assert math.isclose(a,val,rel_tol=1e-6,abs_tol=1e-6),(key,a,val)
qa={'status':'PASS','scope':'summary and selection comparison with independently generated local V6, not old-version data','maximum_numeric_difference':max(diffs.values()),'tolerance':'abs 1e-6 or relative 1e-6','differences':diffs}
(ROOT/'qa/local_remote_comparison.json').write_text(json.dumps(qa,indent=2)+'\n');print(qa)
