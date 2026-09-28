"""Recompute the frozen technical study and verify against the local reference."""
from pathlib import Path
import sys,subprocess,json,math,hashlib,os
ROOT=Path(__file__).resolve().parents[1]

def run(script):
    with (ROOT/'qa'/(script+'.log')).open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'src'/(script+'.py'))],stdout=log,stderr=subprocess.STDOUT,check=True)
for name in ['test_model','study','analyze','audit_v7','make_report']:run(name)
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/v7-lo','--headless','--convert-to','pdf','--outdir',str(ROOT/'report'),str(ROOT/'report/SSBB_V7_Technical_Public.pptx')],check=True)
run('verify_report')
a=json.loads((ROOT/'reference_summary.json').read_text());b=json.loads((ROOT/'results/summary.json').read_text());diff=[]
def cmp(x,y,path=''):
    if isinstance(x,dict):
        assert set(x)==set(y),(path,'keys')
        for k in x:cmp(x[k],y[k],path+'/'+k)
    elif isinstance(x,list):
        assert len(x)==len(y),(path,'length')
        for k,(v,w) in enumerate(zip(x,y)):cmp(v,w,path+'/'+str(k))
    elif isinstance(x,bool) or x is None or isinstance(x,str):assert x==y,(path,x,y)
    else:
        assert math.isclose(float(x),float(y),rel_tol=1e-7,abs_tol=1e-7),(path,x,y)
        diff.append({'path':path,'absolute_difference':abs(float(x)-float(y))})
cmp(a,b)
comp={'status':'PASS','numbers_compared':len(diff),'maximum_absolute_difference':max(v['absolute_difference'] for v in diff),'relative_tolerance':1e-7,'absolute_tolerance':1e-7,'selected_candidate_equal':a['selected']['candidate']==b['selected']['candidate'],'scope':'Recomputed technical study, not hardware validation'}
(ROOT/'qa/local_remote_comparison.json').write_text(json.dumps(comp,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pub={'source_commit':os.environ.get('GITHUB_SHA'),'run_url':os.environ.get('RUN_URL'),'scope':'Public technical material only','specification':b['specification']['user_confirmed'],'runs':b['campaign_runs'],'comparison':comp,'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in [ROOT/'report/SSBB_V7_Technical_Public.pptx',ROOT/'report/SSBB_V7_Technical_Public.pdf',ROOT/'results/summary.json']}}
(ROOT/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n')
run('package_delivery');print(json.dumps(pub,ensure_ascii=False,indent=2))
