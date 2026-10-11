#!/usr/bin/env python3
"""Check relative links and byte-preserved exported media."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import hashlib,json,re,sys
root=Path(__file__).resolve().parents[1]
errors=[]
for p in root.rglob('*'):
 if not p.is_file() or '.git' in p.parts:continue
 if p.suffix in {'.md','.html'}:
  s=p.read_text()
  urls=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',s)+re.findall(r'(?:src|href)=["\']([^"\']+)["\']',s)
  for u in urls:
   if u.startswith('#') or urlsplit(u).scheme:continue
   target=(p.parent/unquote(u.split('#')[0])).resolve()
   if not target.exists():errors.append(f'broken link: {p.relative_to(root)} -> {u}')
 if p.suffix in {'.md','.txt','.json','.html'}:
  s=p.read_text()
  if re.search(r'/Users/|/var/folders/|/mnt/data/',s):errors.append(f'local path: {p.relative_to(root)}')
  if re.search(r'gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN .*PRIVATE KEY-----',s):errors.append(f'credential pattern: {p.relative_to(root)}')
 if p.stat().st_size>=100*1024**2:errors.append(f'oversized file: {p.relative_to(root)}')
manifest=json.loads((root/'文件清单.json').read_text())
for item in manifest['files']:
 p=root/item['path']
 if not p.exists():errors.append(f'missing exported file: {item["path"]}');continue
 if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:errors.append(f'hash mismatch: {item["path"]}')
print(json.dumps({'checked_exported_files':len(manifest['files']),'errors':errors},ensure_ascii=False,indent=2))
sys.exit(bool(errors))
