"""Verify report objects against its frozen numerical specification and required inputs."""
from pathlib import Path
import json,math,hashlib
from pptx import Presentation
import fitz
from model import ROOT,assert_spec
assert_spec()
r=ROOT/'report';q=ROOT/'qa';spec=json.loads((r/'deck_v6.json').read_text());p=r/'SSBB_V6_Submission_BaekSeungwoo.pptx';prs=Presentation(p)
assert len(prs.slides)==len(spec['slides'])==51
nc=nv=nt=cell=links=0
for sl,sd in zip(prs.slides,spec['slides']):
    charts=[sh.chart for sh in sl.shapes if sh.has_chart];ce=[e for e in sd.get('elements',[]) if e['kind']=='chart']
    assert len(charts)==len(ce)
    for c,e in zip(charts,ce):
        assert len(c.series)==len(e['series'])
        for s,z in zip(c.series,e['series']):
            assert len(s.values)==len(z['values'])
            assert all(math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12) for a,b in zip(s.values,z['values']))
            nv+=len(s.values)
        nc+=1
    tables=[sh.table for sh in sl.shapes if sh.has_table];te=[e for e in sd.get('elements',[]) if e['kind']=='table']
    assert len(tables)==len(te)
    for t,e in zip(tables,te):
        for i,row in enumerate(e['rows']):
            for j,x in enumerate(row):
                assert t.cell(i,j).text==str(x);cell+=1
        nt+=1
    assert sl.has_notes_slide and len(sl.notes_slide.notes_text_frame.text)>150
    for sh in sl.shapes:
        assert sh.left>=-100 and sh.top>=-100 and sh.left+sh.width<=prs.slide_width+100 and sh.top+sh.height<=prs.slide_height+100
    links+=len(sl._element.xpath('.//a:hlinkClick'))
# Numeric input checks target generated spec, not incidental old-spec comparisons in text.
plain='\n'.join(sh.text for sl in prs.slides for sh in sl.shapes if sh.has_text_frame)
assert all(v in plain for v in ['230 Vac','48 Arms','Peak dq','16 μs','11.04 kVA'])
assert spec['test_map_page']==7 and spec['glossary_page']==35 and spec['results_page']==23
pdf=r/'SSBB_V6_Submission_BaekSeungwoo.pdf';pd=fitz.open(pdf)
assert len(pd)==51
outside=[];glyph=[]
for i,page in enumerate(pd):
    text=page.get_text();assert len(text)>100
    if '\ufffd' in text:glyph.append(i+1)
    for block in page.get_text('dict')['blocks']:
        if 'lines' not in block:continue
        for ln in block['lines']:
            for sp in ln['spans']:
                x0,y0,x1,y1=sp['bbox']
                if x0<-1 or y0<-1 or x1>page.rect.width+1 or y1>page.rect.height+1:outside.append(dict(page=i+1,text=sp['text'],bbox=sp['bbox']))
assert not outside and not glyph,(outside,glyph)
# Ensure generated report and model use the same source spec; preserve computed failures.
s=json.loads((ROOT/'results/summary.json').read_text());assert s['campaign_runs']==502
assert s['specification']==json.loads((ROOT/'specification.json').read_text())
qa=dict(status='PASS',scope='document object and numerical binding verification, not actual hardware validation',slides=len(pd),main_slides=spec['main_count'],appendix_slides=len(pd)-spec['main_count'],native_charts=nc,chart_values_checked=nv,native_tables=nt,table_cells_checked=cell,notes=len(pd),internal_links=links,pdf_text_outside_page=outside,replacement_glyph_pages=glyph,pptx_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
(q/'report_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(qa,ensure_ascii=False,indent=2))
