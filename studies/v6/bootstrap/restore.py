"""Restore only hash-verified V6 sources into a fresh working directory."""
from pathlib import Path
import base64, hashlib, json, lzma, sys

src = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
if out.exists() and any(out.iterdir()):
    raise RuntimeError('Use an empty destination for a fresh V6 calculation')
manifest = json.loads((src / 'manifest.json').read_text())
packed = base64.b64decode(''.join((src / f'part{i}.b64').read_text().strip() for i in range(1, manifest['parts'] + 1)), validate=True)
if hashlib.sha256(packed).hexdigest() != manifest['archive_sha256']:
    raise RuntimeError('Compressed source SHA-256 mismatch')
files = json.loads(lzma.decompress(packed))
if set(files) != set(manifest['files']):
    raise RuntimeError('Source filename manifest mismatch')
for name, text in files.items():
    p = (out / name).resolve()
    if not p.is_relative_to(out) or not isinstance(text, str):
        raise RuntimeError(f'Invalid source entry: {name}')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != manifest['files'][name]:
        raise RuntimeError(f'Source SHA-256 mismatch: {name}')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
for name in ['qa', 'results', 'waveforms', 'report']:
    (out / name).mkdir(exist_ok=True)
print(f'Verified and restored {len(files)} V6 source files into {out}')
