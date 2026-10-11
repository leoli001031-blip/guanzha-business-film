"""把 创意库/ 下的全部 markdown 合成一个离线网页：左侧目录，右侧全文，标签可点选过滤。

用法: python render_library.py <创意库目录> <输出.html>
"""
import glob
import html
import os
import re
import sys

src_dir, out_path = sys.argv[1], sys.argv[2]
files = sorted(f for f in glob.glob(os.path.join(src_dir, '*.md')) if not os.path.basename(f).startswith('00-'))


def inline(text):
    codes = []

    def stash(m):
        codes.append(html.escape(m.group(1), quote=False))
        return f'\x01{len(codes) - 1}\x01'

    text = re.sub(r'`(.+?)`', stash, text)
    keep = text.replace('<br>', '\x00')
    out = html.escape(keep, quote=False)
    out = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', out)
    out = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', out)
    out = re.sub(r'(?<![\w/])#([一-鿿A-Za-z0-9]+)', r'<span class="tag" data-tag="\1">#\1</span>', out)
    out = re.sub(r'\x01(\d+)\x01', lambda m: f'<code>{codes[int(m.group(1))]}</code>', out)
    return out.replace('\x00', '<br>')


def table(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    head, body = cells[0], cells[2:]
    out = ['<div class="tw"><table><thead><tr>']
    out += [f'<th>{inline(h)}</th>' for h in head]
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


def render_md(md, prefix):
    body, lines, i, title, h3s = [], md.splitlines(), 0, '', []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('# '):
            title = ln[2:].strip()
            body.append(f'<h1>{inline(title)}</h1>')
        elif ln.startswith('## '):
            body.append(f'<h2>{inline(ln[3:])}</h2>')
        elif ln.startswith('### '):
            h = ln[4:].strip()
            hid = f'{prefix}-{len(h3s)}'
            h3s.append((hid, h))
            body.append(f'<h3 id="{hid}">{inline(h)}</h3>')
        elif ln.startswith('#### '):
            body.append(f'<h4>{inline(ln[5:])}</h4>')
        elif ln.strip() == '---':
            body.append('<hr>')
        elif ln.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            body.append(table(rows))
            continue
        elif re.match(r'^\s*[-*] ', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*] ', lines[i]):
                items.append(f'<li>{inline(re.sub(r"^\s*[-*] ", "", lines[i]))}</li>')
                i += 1
            body.append('<ul>' + ''.join(items) + '</ul>')
            continue
        elif re.match(r'^\s*\d+[.、] ', ln):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+[.、] ', lines[i]):
                items.append(f'<li>{inline(re.sub(r"^\s*\d+[.、] ", "", lines[i]))}</li>')
                i += 1
            body.append('<ol>' + ''.join(items) + '</ol>')
            continue
        elif ln.startswith('> '):
            q = []
            while i < len(lines) and lines[i].startswith('>'):
                q.append(inline(lines[i].lstrip('> ').strip()))
                i += 1
            body.append('<blockquote>' + '<br>'.join(q) + '</blockquote>')
            continue
        elif ln.strip():
            # 「一句话：」这类字段行单独成段，方便扫读
            m = re.match(r'^(一句话|适合|怎么做|信息落点|代价|和 r8 的关系|标签)[：:]\s*(.*)$', ln.strip())
            if m:
                body.append(f'<p class="field"><b>{m.group(1)}</b>{inline(m.group(2))}</p>')
            else:
                body.append(f'<p>{inline(ln)}</p>')
        i += 1
    return title, ''.join(body), h3s


sections, nav, all_tags = [], [], {}
for n, f in enumerate(files):
    md = open(f, encoding='utf-8').read()
    name = os.path.basename(f)[:-3]
    title, body_html, h3s = render_md(md, f'd{n}')
    for t in re.findall(r'(?<![\w/])#([一-鿿A-Za-z0-9]+)', md):
        all_tags[t] = all_tags.get(t, 0) + 1
    sections.append(f'<section id="d{n}" class="doc">{body_html}</section>')
    sub = ''.join(f'<li><a href="#{hid}">{html.escape(h)}</a></li>' for hid, h in h3s[:60])
    nav.append(f'<li class="top"><a href="#d{n}">{html.escape(name)}</a><ul>{sub}</ul></li>')

tag_buttons = ''.join(
    f'<button class="tb" data-tag="{html.escape(t)}">#{html.escape(t)} <small>{c}</small></button>'
    for t, c in sorted(all_tags.items(), key=lambda x: -x[1]) if c >= 2)

page = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>观猹漫剧 创意库</title>
<style>
:root {{ --bg:#f6f7f4; --paper:#fff; --ink:#1d231f; --muted:#66706a; --line:#dfe4dd; --accent:#2f7d4f; --accent-soft:#e6f2ea; --head:#eef1ec; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#121513; --paper:#1a1e1b; --ink:#e6ebe7; --muted:#9aa59e; --line:#2c332e; --accent:#6cc28f; --accent-soft:#1f3327; --head:#222824; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.7 "PingFang SC","Microsoft YaHei","Noto Sans SC",sans-serif; }}
.wrap {{ display:flex; min-height:100vh; }}
aside {{ width:300px; flex:none; position:sticky; top:0; height:100vh; overflow:auto; padding:16px; border-right:1px solid var(--line); background:var(--paper); font-size:13px; }}
aside h1 {{ font-size:16px; margin:0 0 8px; }}
aside input {{ width:100%; padding:6px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); margin-bottom:10px; }}
aside ul {{ list-style:none; padding:0; margin:0; }}
aside li.top {{ margin:6px 0; }}
aside li.top > a {{ font-weight:600; color:var(--ink); text-decoration:none; }}
aside li.top ul {{ padding-left:10px; border-left:2px solid var(--line); margin:2px 0 6px; display:none; }}
aside li.top.open ul {{ display:block; }}
aside li.top ul a {{ color:var(--muted); text-decoration:none; display:block; padding:1px 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
aside a:hover {{ color:var(--accent); }}
.tags {{ display:flex; flex-wrap:wrap; gap:4px; margin:8px 0 12px; }}
.tb {{ font-size:12px; border:1px solid var(--line); background:var(--bg); color:var(--accent); border-radius:999px; padding:1px 8px; cursor:pointer; }}
.tb.on {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
main {{ flex:1; min-width:0; padding:24px 32px 80px; max-width:1100px; }}
section.doc {{ background:var(--paper); border:1px solid var(--line); border-radius:12px; padding:20px 26px; margin-bottom:28px; scroll-margin-top:12px; }}
h1 {{ font-size:24px; margin:4px 0 10px; }}
h2 {{ font-size:18px; margin:28px 0 8px; border-top:2px solid var(--accent); padding-top:12px; }}
h3 {{ font-size:16px; margin:22px 0 6px; scroll-margin-top:12px; }}
h4 {{ font-size:15px; margin:14px 0 4px; color:var(--muted); }}
p {{ margin:6px 0; }}
p.field {{ margin:3px 0; padding-left:10px; border-left:3px solid var(--line); }}
p.field b {{ color:var(--muted); font-weight:500; margin-right:8px; }}
.tag {{ color:var(--accent); background:var(--accent-soft); border-radius:4px; padding:0 5px; font-size:13px; margin-right:2px; }}
.tw {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; margin:8px 0; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ text-align:left; vertical-align:top; padding:6px 9px; border-bottom:1px solid var(--line); }}
th {{ background:var(--head); font-weight:600; color:var(--muted); white-space:nowrap; }}
tbody tr:last-child td {{ border-bottom:0; }}
blockquote {{ margin:8px 0; padding:6px 12px; border-left:3px solid var(--accent); background:var(--accent-soft); border-radius:0 6px 6px 0; }}
code {{ background:var(--head); padding:0 4px; border-radius:4px; }}
hr {{ border:0; border-top:1px solid var(--line); margin:20px 0; }}
.hide {{ display:none; }}
mark {{ background:#ffe58a; color:#000; }}
@media (max-width:900px) {{ .wrap {{ flex-direction:column; }} aside {{ position:static; width:auto; height:auto; max-height:40vh; }} main {{ padding:16px; }} }}
@media print {{ aside {{ display:none; }} section.doc {{ break-inside:auto; }} }}
</style>
</head>
<body>
<div class="wrap">
<aside>
<h1>观猹漫剧 · 创意库</h1>
<input id="q" type="search" placeholder="全文搜索（回车高亮）">
<div class="tags">{tag_buttons}</div>
<ul id="nav">{''.join(nav)}</ul>
</aside>
<main>
{''.join(sections)}
</main>
</div>
<script>
(function(){{
  // 目录：点文件名展开小节
  document.querySelectorAll('#nav li.top > a').forEach(a => a.addEventListener('click', e => {{ a.parentElement.classList.toggle('open'); }}));
  // 标签过滤：只显示含该标签的 h3 小块（h3 到下一个 h3/h2 之间）
  let active = null;
  function blocks() {{
    const out = [];
    document.querySelectorAll('section.doc').forEach(sec => {{
      let cur = null;
      Array.from(sec.children).forEach(el => {{
        if (el.tagName === 'H3') {{ cur = {{ head: el, els: [] }}; out.push(cur); }}
        else if (el.tagName === 'H2' || el.tagName === 'H1') {{ cur = null; }}
        else if (cur) cur.els.push(el);
      }});
    }});
    return out;
  }}
  const BL = blocks();
  function applyTag(tag) {{
    BL.forEach(b => {{
      const text = [b.head, ...b.els].map(e => e.textContent).join(' ');
      const show = !tag || text.includes('#' + tag);
      [b.head, ...b.els].forEach(e => e.classList.toggle('hide', !show));
    }});
  }}
  document.querySelectorAll('.tb').forEach(btn => btn.addEventListener('click', () => {{
    const t = btn.dataset.tag;
    active = (active === t) ? null : t;
    document.querySelectorAll('.tb').forEach(b => b.classList.toggle('on', b.dataset.tag === active));
    applyTag(active);
  }}));
  document.querySelectorAll('span.tag').forEach(s => s.addEventListener('click', () => {{
    const btn = document.querySelector('.tb[data-tag="' + s.dataset.tag + '"]'); if (btn) btn.click();
  }}));
  // 搜索高亮
  const q = document.getElementById('q');
  q.addEventListener('keydown', e => {{
    if (e.key !== 'Enter') return;
    document.querySelectorAll('mark').forEach(m => m.replaceWith(m.textContent));
    const kw = q.value.trim(); if (!kw) return;
    const walker = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
    const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
    let first = null;
    nodes.forEach(n => {{
      const i = n.nodeValue.indexOf(kw); if (i < 0) return;
      const span = document.createElement('span');
      span.innerHTML = n.nodeValue.split(kw).map(s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;')).join('<mark>' + kw + '</mark>');
      n.replaceWith(span); if (!first) first = span;
    }});
    if (first) first.scrollIntoView({{ block: 'center' }});
  }});
}})();
</script>
</body>
</html>
"""
open(out_path, 'w', encoding='utf-8').write(page)
print(out_path, f'{len(files)} docs, {len(page)} bytes, tags: {len(all_tags)}')
