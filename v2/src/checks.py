"""Execute tests, store real results, refresh report and all output hashes."""
from pathlib import Path
import unittest, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    info=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),passed=result.wasSuccessful())
    (ROOT/'results/test_report.json').write_text(json.dumps(info,indent=2))
    if not result.wasSuccessful(): raise SystemExit(1)
    from .report import build
    build(ROOT)
    manifest={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.name not in ['manifest.json','run.log','checks.log','publication.json']}
    (ROOT/'results/manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
