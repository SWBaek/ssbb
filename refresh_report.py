"""Rebuild report/metadata without changing frozen numerical results."""
from pathlib import Path
import json, sys, platform
import numpy, scipy, numba, pandas, matplotlib
from src.report import build_report
from src.study import sha, write_json
root=Path(__file__).parent
build_report(root)
write_json(root/'results/environment.json',dict(python=sys.version,platform=platform.platform(),numpy=numpy.__version__,scipy=scipy.__version__,numba=numba.__version__,pandas=pandas.__version__,matplotlib=matplotlib.__version__,source_hashes={str(p.relative_to(root)):sha(p) for p in sorted((root/'src').glob('*.py'))}))
paths=sorted(p for folder in ['results','data','report'] for p in (root/folder).rglob('*') if p.is_file() and p.name!='manifest.json')
write_json(root/'results/manifest.json',dict(algorithm='SHA-256',files=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]))
