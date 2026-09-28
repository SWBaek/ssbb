"""Package only public technical V7 material; never include internal submission files."""
from pathlib import Path
import json,hashlib,zipfile,shutil,os
from model import ROOT

def main():
    out=Path(os.environ.get('V7_DELIVERY_DIR',str(ROOT.parent/'v7_public_delivery')));out.mkdir(parents=True,exist_ok=True)
    def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    for suf in ['.pptx','.pdf']:
        p=ROOT/'report'/('SSBB_V7_Technical_Public'+suf);shutil.copy2(p,out/p.name)
    core=out/'SSBB_V7_Technical_Study.zip'
    included=[]
    with zipfile.ZipFile(core,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file():continue
            rel=p.relative_to(ROOT)
            if any(a in rel.parts for a in ['waveforms','__pycache__','bootstrap','renders']):continue
            if rel.name.endswith(('.nbc','.nbi','.pyc','.pid')):continue
            if rel.parts[0] not in ['src','docs','results','qa','report','sources'] and rel.name not in ['specification.json','requirements.txt','README.md','source_lineage.json','reference_summary.json','publication.json']:continue
            z.write(p,'ssbb_v7/'+rel.as_posix());included.append(rel.as_posix())
    # npz files are already compressed. Avoid repeated compression and keep each ZIP independent.
    groups=[];current=[];size=0
    for p in sorted((ROOT/'waveforms').glob('*.npz')):
        if current and size+p.stat().st_size>80*1024**2:groups.append(current);current=[];size=0
        current.append(p);size+=p.stat().st_size
    if current:groups.append(current)
    assert sum(len(x) for x in groups)==502
    raw=[]
    for i,group in enumerate(groups,1):
        p=out/f'SSBB_V7_RawWaveforms_{i:02d}.zip'
        with zipfile.ZipFile(p,'w',zipfile.ZIP_STORED) as z:
            for f in group:z.write(f,'ssbb_v7/waveforms/'+f.name)
        raw.append({'filename':p.name,'runs':len(group),'bytes':p.stat().st_size,'sha256':h(p)})
    allfiles=[out/'SSBB_V7_Technical_Public.pptx',out/'SSBB_V7_Technical_Public.pdf',core]
    manifest={'version':'V7','spec':'240 Vac / 48 Arms / 11520 VA / Peak dq / PWM=control=62500Hz / 16us','raw_run_count':502,'raw_parts':raw,'core_included_files':included,'artifacts':{p.name:{'bytes':p.stat().st_size,'sha256':h(p)} for p in allfiles},'scope':'Public technical edition only. No company guide or internal submission material.'}
    (out/'SSBB_V7_Public_Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'core':core.stat().st_size,'raw_parts':len(raw),'raw_bytes':sum(x['bytes'] for x in raw)},indent=2))
if __name__=='__main__':main()
