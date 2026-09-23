"""Optional browser rendering QA; uses Playwright and a locally installed Chromium."""
import asyncio,json,shutil
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
 async with async_playwright() as p:
  options=dict(headless=True,args=['--no-sandbox'])
  if shutil.which('chromium'): options['executable_path']=shutil.which('chromium')
  b=await p.chromium.launch(**options);pg=await b.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
  errors=[];pg.on('pageerror',lambda e:errors.append(str(e)))
  await pg.set_content((ROOT/'report/index.html').read_text(),wait_until='load');await pg.wait_for_timeout(300)
  issues=[];count=await pg.locator('.slide').count();scans=[]
  for i in range(count):
   await pg.evaluate('(i)=>show(i)',i)
   m=await pg.locator('.slide.active').evaluate('(e)=>({height:e.getBoundingClientRect().height,width:e.getBoundingClientRect().width,scrollWidth:e.scrollWidth,clientWidth:e.clientWidth})')
   scans.append({'slide':i+1,**m})
   if m['scrollWidth']>m['clientWidth']+1:issues.append({'slide':i+1,**m})
  for i in [0,2,8,15,19,23,24,27,28]:
   if i>=count:continue
   await pg.evaluate('(i)=>show(i)',i)
   await pg.screenshot(path=str(ROOT.parent/f'v2_preview_{i+1:02}.png'),full_page=True)
  await pg.set_viewport_size({'width':430,'height':932});await pg.evaluate('show(15)')
  await pg.screenshot(path=str(ROOT.parent/'v2_mobile.png'),full_page=True)
  mobi=await pg.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
  out={'slides':count,'horizontal_overflow':issues,'desktop_heights':scans,'mobile':mobi,'page_errors':errors}
  (ROOT/'results/html_qa.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));await b.close()
  if issues or errors or mobi['scroll']>mobi['width']+1:raise SystemExit('HTML QA failed')
asyncio.run(main())
