"""Reconstruct only hash-verified V7 sources; never restore old numerical results."""
from pathlib import Path
import base64, hashlib, json, lzma, subprocess, sys

src = Path(__file__).resolve().parent
out = Path(sys.argv[1]).resolve()
if out.exists() and any(out.iterdir()):
    raise RuntimeError('The V7 destination must be empty')
manifest = json.loads((src / 'manifest.json').read_text())
packed = base64.b64decode(''.join((src / f'part{i}.b64').read_text().strip() for i in range(1, manifest['parts'] + 1)), validate=True)
if hashlib.sha256(packed).hexdigest() != manifest['archive_sha256']:
    raise RuntimeError('Compressed source SHA-256 mismatch')
payload = json.loads(lzma.decompress(packed))
if payload['base_commit'] != manifest['base_commit']:
    raise RuntimeError('Pinned source commit mismatch')
if set(payload['files']) != set(manifest['files']):
    raise RuntimeError('Source filename manifest mismatch')
for name, entry in payload['files'].items():
    p = (out / name).resolve()
    if not p.is_relative_to(out):
        raise RuntimeError(f'Unsafe path: {name}')
    if 'text' in entry:
        text = entry['text']
    else:
        raw = subprocess.check_output(['git', 'show', payload['base_commit'] + ':' + entry['upstream_path']])
        if hashlib.sha256(raw).hexdigest() != entry['upstream_sha256']:
            raise RuntimeError(f'Pinned implementation SHA-256 mismatch: {name}')
        lines = raw.decode('utf-8').splitlines(keepends=True)
        chunks = []
        for op in entry['ops']:
            if 'copy' in op:
                first, last = op['copy']
                if not 0 <= first <= last <= len(lines):
                    raise RuntimeError(f'Invalid line range: {name}')
                chunks.append(''.join(lines[first:last]))
            else:
                chunks.append(op['text'])
        text = ''.join(chunks)
    if not isinstance(text, str) or hashlib.sha256(text.encode('utf-8')).hexdigest() != manifest['files'][name]:
        raise RuntimeError(f'Reconstructed source SHA-256 mismatch: {name}')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
for name in ['qa', 'results', 'waveforms', 'report']:
    (out / name).mkdir(exist_ok=True)
print(f'Verified and restored {len(payload["files"])} V7 source files into {out}')
