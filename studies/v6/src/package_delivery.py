"""Package V6 auditable study and raw data without fonts or previous versions."""
from pathlib import Path
import json,hashlib,zipfile,shutil,platform,sys,os
from model import ROOT

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()
def main():
    out=Path(os.environ.get('V6_DELIVERY_DIR',str(ROOT.parent/'v6_delivery')));out.mkdir(parents=True,exist_ok=True)
    allowed=[]
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():continue
        r=p.relative_to(ROOT)
        if any(x in ['__pycache__','renders','bootstrap','.git'] for x in r.parts):continue
        if p.suffix in ['.pyc','.nbc','.nbi','.pid'] or p.name in ['delivery_manifest.json','publication.json']:continue
        allowed.append(p)
    manifest={'study_id':'SSBB-V6-20260928','python':sys.version,'platform':platform.platform(),'raw_count':len(list((ROOT/'waveforms').glob('*.npz'))),'files':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in allowed}}
    (ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    core=[p for p in allowed if p.parent.name!='waveforms']+[ROOT/'delivery_manifest.json']
    zp=out/'SSBB_V6_Study_and_Report.zip'
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in core:z.write(p,'ssbb_v6/'+str(p.relative_to(ROOT)))
    waves=[p for p in allowed if p.parent.name=='waveforms'];groups=[];batch=[];n=0
    for p in waves:
        if batch and n+p.stat().st_size>80*1024**2:groups.append(batch);batch=[];n=0
        batch.append(p);n+=p.stat().st_size
    if batch:groups.append(batch)
    for k,batch in enumerate(groups,1):
        with zipfile.ZipFile(out/f'SSBB_V6_RawWaveforms_{k:02d}.zip','w',zipfile.ZIP_STORED) as z:
            for p in batch:z.write(p,'ssbb_v6/waveforms/'+p.name)
    for ext in ['pptx','pdf']:
        p=ROOT/'report'/f'SSBB_V6_Submission_BaekSeungwoo.{ext}';shutil.copy2(p,out/p.name)
    assets={p.name:{'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(out.glob('*')) if p.is_file() and p.name!='SSBB_V6_assets.json'}
    (out/'SSBB_V6_assets.json').write_text(json.dumps(assets,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(output=str(out),raw_count=len(waves),raw_parts=len(groups),assets=assets),indent=2))
if __name__=='__main__':main()
