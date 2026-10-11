"""把文字分镜 markdown 渲染成一个离线可看的 HTML 页面。

用法: python render_storyboard.py <分镜.md> <输出.html>
"""
import html
import re
import sys

src_path, out_path = sys.argv[1], sys.argv[2]
md = open(src_path, encoding='utf-8').read()

# 每场时长，用来在场次标题旁边标出时间
scene_dur = {}
for no, body in re.findall(r'(?ms)^## (\d\d)｜(.*?)(?=^## |\Z)', md):
    scene_dur[no] = sum(float(x) for x in re.findall(r'(?m)^\| \d+-\d+ \| ([\d.]+) 秒', body))
starts, acc = {}, 0.0
for no in sorted(scene_dur):
    starts[no] = acc
    acc += scene_dur[no]
total = acc


def mmss(x):
    return f"{int(x // 60)}:{int(round(x % 60)):02d}"


def inline(text):
    codes = []

    def stash(m):
        codes.append(html.escape(m.group(1), quote=False))
        return f'\x01{len(codes) - 1}\x01'

    text = re.sub(r'`(.+?)`', stash, text)
    keep = text.replace('<br>', '\x00')
    out = html.escape(keep, quote=False)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'\x01(\d+)\x01', lambda m: f'<code>{codes[int(m.group(1))]}</code>', out)
    out = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', out)
    return out.replace('\x00', '<br>')


def vo_cell(text):
    if text.strip() == '—':
        return '<span class="none">—</span>'
    lines = []
    for sub in text.split('<br>'):
        sub = sub.strip()
        m = re.match(r'^(无线电|商务猹)：(.*)$', sub)
        if m:
            lines.append(f'<span class="sub"><span class="who">{m.group(1)}</span>{inline(m.group(2))}</span>')
        else:
            lines.append(f'<span class="sub">{inline(sub)}</span>')
    return ''.join(lines)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], cells[2:]
    sb = head and head[0] == '镜号'
    names = {'镜号': 'c-no', '时长': 'c-dur', '景别 / 运镜': 'c-cam', '画面': 'c-pic',
             '画面信息': 'c-info', '旁白 / 台词': 'c-vo', '声音': 'c-sfx'}
    col = [names.get(h, '') if sb else '' for h in head]
    cls = ' class="sb"' if sb else ''
    out = [f'<div class="tw"><table{cls}><thead><tr>']
    out += [f'<th class="{col[i]}">{inline(h)}</th>' for i, h in enumerate(head)]
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>')
        for i, c in enumerate(r):
            k = col[i] if i < len(col) else ''
            if k == 'c-vo':
                out.append(f'<td class="{k}">{vo_cell(c)}</td>')
            elif k == 'c-pic':
                pic = re.sub(r'【(.+?)】', r'<span class="cam">\1</span>', inline(c))
                out.append(f'<td class="{k}">{pic}</td>')
            else:
                out.append(f'<td class="{k}">{inline(c)}</td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


body, lines, i = [], md.splitlines(), 0
title = '文字分镜'
while i < len(lines):
    ln = lines[i]
    if ln.startswith('# '):
        title = ln[2:].strip()
        body.append(f'<h1>{inline(title)}</h1>')
    elif ln.startswith('## '):
        h = ln[3:].strip()
        m = re.match(r'(\d\d)｜', h)
        if m and m.group(1) in scene_dur:
            no = m.group(1)
            badge = f'<span class="badge">{mmss(starts[no])}–{mmss(starts[no] + scene_dur[no])} · {scene_dur[no]:.1f} 秒</span>'
            body.append(f'<h2 id="s{no}" class="scene">{inline(h)}{badge}</h2>')
        else:
            body.append(f'<h2>{inline(h)}</h2>')
    elif ln.startswith('### '):
        body.append(f'<h3>{inline(ln[4:])}</h3>')
    elif ln.strip() == '---':
        body.append('<hr>')
    elif ln.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            rows.append(lines[i])
            i += 1
        body.append(table(rows))
        continue
    elif re.match(r'^- ', ln):
        items = []
        while i < len(lines) and re.match(r'^- ', lines[i]):
            items.append(f'<li>{inline(lines[i][2:])}</li>')
            i += 1
        body.append('<ul>' + ''.join(items) + '</ul>')
        continue
    elif re.match(r'^\d+\. ', ln):
        items = []
        while i < len(lines) and re.match(r'^\d+\. ', lines[i]):
            items.append(f'<li>{inline(re.sub(r"^\d+\. ", "", lines[i]))}</li>')
            i += 1
        body.append('<ol>' + ''.join(items) + '</ol>')
        continue
    elif ln.strip():
        body.append(f'<p>{inline(ln)}</p>')
    i += 1

nav = ''.join(f'<a href="#s{no}">{no}</a>' for no in sorted(scene_dur))

page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{
  --bg: #f6f7f4; --paper: #ffffff; --ink: #1d231f; --muted: #66706a; --line: #dfe4dd;
  --accent: #2f7d4f; --accent-soft: #e6f2ea; --vo: #f3f7f1; --head: #eef1ec;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #121513; --paper: #1a1e1b; --ink: #e6ebe7; --muted: #9aa59e; --line: #2c332e;
    --accent: #6cc28f; --accent-soft: #1f3327; --vo: #18241d; --head: #222824;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.7 "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif; }}
nav {{ position: sticky; top: 0; z-index: 5; display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
  padding: 10px 24px; background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--line); }}
nav .t {{ font-weight: 600; margin-right: 10px; }}
nav a {{ color: var(--accent); text-decoration: none; padding: 2px 9px; border: 1px solid var(--line);
  border-radius: 999px; font-variant-numeric: tabular-nums; }}
nav a:hover {{ background: var(--accent-soft); }}
nav .total {{ margin-left: auto; color: var(--muted); }}
main {{ max-width: 1280px; margin: 0 auto; padding: 24px 24px 80px; }}
h1 {{ font-size: 26px; margin: 8px 0 4px; }}
h2 {{ font-size: 19px; margin: 36px 0 8px; padding-top: 8px; }}
h2.scene {{ display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap;
  border-top: 2px solid var(--accent); padding-top: 14px; scroll-margin-top: 60px; }}
.badge {{ font-size: 13px; font-weight: 500; color: var(--accent); background: var(--accent-soft);
  padding: 1px 10px; border-radius: 999px; font-variant-numeric: tabular-nums; }}
p, li {{ color: var(--ink); }}
a {{ color: var(--accent); }}
hr {{ border: 0; border-top: 1px solid var(--line); margin: 32px 0; }}
code {{ background: var(--head); padding: 0 4px; border-radius: 4px; }}
.tw {{ overflow-x: auto; background: var(--paper); border: 1px solid var(--line); border-radius: 10px; margin: 10px 0 6px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; vertical-align: top; padding: 8px 10px; border-bottom: 1px solid var(--line); }}
th {{ background: var(--head); font-weight: 600; font-size: 13px; color: var(--muted); white-space: nowrap; }}
tbody tr:last-child td {{ border-bottom: 0; }}
.c-no {{ width: 58px; }}
.c-dur {{ width: 64px; }}
td.c-no, td.c-dur {{ font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 600; }}
.c-cam {{ width: 130px; color: var(--muted); }}
.c-info {{ width: 210px; font-size: 14px; }}
td.c-info {{ color: var(--accent); }}
.c-vo {{ width: 260px; }}
td.c-vo {{ background: var(--vo); }}
.c-sfx {{ width: 150px; color: var(--muted); font-size: 14px; }}
.cam {{ display: inline-block; font-size: 12px; color: var(--muted); border: 1px solid var(--line);
  border-radius: 4px; padding: 0 5px; margin-right: 6px; }}
.sub {{ display: block; padding-left: 8px; border-left: 3px solid var(--accent); margin: 2px 0; }}
.who {{ display: inline-block; font-size: 12px; color: var(--paper); background: var(--accent);
  border-radius: 4px; padding: 0 5px; margin-right: 6px; }}
.none {{ color: var(--muted); }}
@media (max-width: 760px) {{ main {{ padding: 16px; }} nav {{ padding: 8px 16px; }} }}
@media print {{ nav {{ display: none; }} body {{ background: #fff; }} tr {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<nav><span class="t">{html.escape(title)}</span>{nav}{f'<span class="total">合计约 {mmss(total)}</span>' if scene_dur else ''}</nav>
<main>
{''.join(body)}
</main>
</body>
</html>
"""
open(out_path, 'w', encoding='utf-8').write(page)
print(out_path, f'{len(page)} bytes, {len(scene_dur)} scenes, total {mmss(total)}')
