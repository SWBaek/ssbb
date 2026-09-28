"""Run all V6 calculations in fresh directories, verify, and prepare publication."""
from pathlib import Path
import sys,subprocess,json,os,hashlib,shutil,time
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for d in ['results','qa','waveforms','report']:(ROOT/d).mkdir(exist_ok=True)
assert not list((ROOT/'waveforms').glob('*.npz')),'Reproduction requires empty raw-data directory'
start=time.time()
for name in ['test_model.py','study.py','analyze.py','compare_reference.py','make_report.py']:
    print('RUN',name,flush=True)
    p=subprocess.run([sys.executable,str(ROOT/'src'/name)],capture_output=True,text=True)
    (ROOT/'qa'/('remote_'+name+'.log')).write_text(p.stdout+p.stderr)
    print(p.stdout[-3000:],flush=True)
    if p.returncode:print(p.stderr,flush=True);raise SystemExit(p.returncode)
subprocess.run(['libreoffice','-env:UserInstallation=file:///tmp/ssbb-v6-remote-lo','--headless','--convert-to','pdf','--outdir',str(ROOT/'report'),str(ROOT/'report/SSBB_V6_Submission_BaekSeungwoo.pptx')],check=True)
subprocess.run([sys.executable,str(ROOT/'src/verify_report.py')],check=True)
subprocess.run([sys.executable,str(ROOT/'src/package_delivery.py')],check=True)
out=Path(os.environ['V6_DELIVERY_DIR']);assets=json.loads((out/'SSBB_V6_assets.json').read_text())
pub={'version':'V6','status':'calculation and document verification complete; publication is recorded by workflow and release','source_commit':os.environ.get('GITHUB_SHA'),'run_url':os.environ.get('RUN_URL'),'elapsed_s':time.time()-start,'spec_sha256':hashlib.sha256((ROOT/'specification.json').read_bytes()).hexdigest(),'campaign_runs':502,'confirmed_inputs':{'vac_v':230,'rated_rms_a':48,'external_dq':'Peak A','pwm_hz':62500,'control_hz':62500,'period_us':16},'product_class_label_kva':11.52,'computed_nominal_kva':11.04,'assets':assets}
(ROOT/'publication.json').write_text(json.dumps(pub,ensure_ascii=False,indent=2)+'\n');shutil.copy2(ROOT/'publication.json',out/'publication.json')
print(json.dumps(pub,indent=2),flush=True)
