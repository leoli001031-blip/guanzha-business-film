#!/usr/bin/env python3
"""Export project documents and media; run with a local project directory argument."""
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
import argparse, hashlib, json, os, re, shutil

parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
args=parser.parse_args()
source=args.source.resolve()
repo=Path(__file__).resolve().parents[1]
allowed={'.md','.txt','.json','.html','.png','.jpg','.jpeg','.webp','.svg','.pdf','.mp3','.wav','.mp4'}
files=[p for p in source.rglob('*') if p.is_file() and repo not in p.parents and not any(x.startswith('.') for x in p.relative_to(source).parts) and p.suffix.lower() in allowed]
known={p.relative_to(source).as_posix() for p in files}
manifest=[]

def route(url,parent):
    decoded=unquote(url)
    if decoded.endswith('.zip') and not urlsplit(decoded).scheme:
        return quote(os.path.relpath(repo/'DOWNLOADS.md',parent),safe='/.-_')
    if decoded.startswith(str(source)+'/'):
        rel=decoded[len(str(source))+1:]
        return quote(os.path.relpath(repo/rel,parent),safe='/.-_')
    if decoded.startswith('/Users/') and '/Downloads/' in decoded and decoded.endswith('观猹业务漫剧-脚本重写提案-r3.md'):
        return quote(os.path.relpath(repo/'脚本/观猹业务漫剧-脚本重写提案-r3.md',parent),safe='/.-_')
    if decoded.startswith(('/Users/','/var/folders/','/mnt/data/')):
        return quote(os.path.relpath(repo/'PUBLICATION.md',parent),safe='/.-_')
    if not urlsplit(decoded).scheme and not decoded.startswith('#'):
        target=(parent/decoded).resolve()
        if decoded.endswith('.zip'):
            return quote(os.path.relpath(repo/'DOWNLOADS.md',parent),safe='/.-_')
        if decoded.endswith('.py') and not target.exists():
            return quote(os.path.relpath(repo/'PUBLICATION.md',parent),safe='/.-_')
    return url

# Source context UUIDs and workstation paths aren't project content.
def clean(s):
    s=s.replace(str(source),'[项目目录]')
    s=re.sub(r'/Users/[^\s`"<>\]\)\n,，；。]+','[本地路径已省略]',s)
    s=re.sub(r'/(?:var/folders|mnt/data)/[^\s`"<>\]\)\n,，；。]+','[临时路径已省略]',s)
    s=re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b','[本地记录编号已省略]',s)
    s=re.sub(r'https?://[^\s"<>]*(?:asynccode|[?&](?:signature|access_token)=)[^\s"<>]*','[临时下载地址已省略]',s)
    return s

def json_clean(x):
    if isinstance(x,dict):
        return {k:('[已省略]' if re.fullmatch(r'(?:api_key|access_token|refresh_token|authorization|password|secret|cookie)',k,re.I) else json_clean(v)) for k,v in x.items()}
    if isinstance(x,list):return [json_clean(v) for v in x]
    if isinstance(x,str):return clean(x)
    return x

for p in files:
    rel=p.relative_to(source)
    dest=repo/rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    raw=p.read_bytes()
    if p.suffix.lower() in {'.md','.txt','.json','.html'}:
        s=raw.decode('utf-8')
        if p.suffix=='.json':
            s=json.dumps(json_clean(json.loads(s)),ensure_ascii=False,indent=2)+'\n'
        else:
            s=re.sub(r'(!?\[[^\]]*\]\()([^\)]+)\)',lambda m:m[1]+route(m[2],dest.parent)+')',s)
            s=re.sub(r'((?:src|href)=["\'])([^"\']+)(["\'])',lambda m:m[1]+route(m[2],dest.parent)+m[3],s)
            s=clean(s)
        dest.write_text(s,encoding='utf-8')
    else:shutil.copy2(p,dest)
    blob=dest.read_bytes()
    manifest.append({'path':rel.as_posix(),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'original_media_unchanged': p.suffix.lower() not in {'.md','.txt','.json','.html'}})
(repo/'文件清单.json').write_text(json.dumps({'date':'2026-10-11','files':manifest},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'exported':len(files),'images':sum(p.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.svg'} for p in files),'bytes':sum(i['bytes'] for i in manifest)},ensure_ascii=False))
