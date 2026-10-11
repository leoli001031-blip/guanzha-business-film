"""校验并整理文字分镜。

检查：每条字幕不超过 16 个汉字；每个镜头的旁白念得完（按每秒 3.7 字、英文词 0.4 秒估）。
整理（--fill）：按镜头时长填"时长"表、合计行，并把旁白全文生成到文末的 {VO_FULLTEXT} 占位处。

用法:
    python tools/check_storyboard.py 分镜/观猹业务漫剧-文字分镜-r8.md
    python tools/check_storyboard.py 分镜/观猹业务漫剧-文字分镜-r8.md --fill
    python tools/check_storyboard.py 分镜/xxx.md --rate 4.0      # 换一个语速估算

分镜表格式：| 镜号 | 时长 | 画面 | 画面信息 | 旁白 / 台词 | 声音 |（也兼容旧的 6 列"景别 / 运镜"版）。
旁白栏里 <br> 是字幕断点；"无线电：""商务猹："开头的是台词。
"""
import argparse
import re
import sys

SPEAKERS = r'(无线电|商务猹)：'


def mmss(x):
    return f"{int(x // 60)}:{int(round(x % 60)):02d}"


def han(s):
    return len(re.findall(r'[一-鿿]', s))


def eng(s):
    return len(re.findall(r'[A-Za-z]+', s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--fill', action='store_true', help='回填时长表、合计行和旁白全文')
    ap.add_argument('--rate', type=float, default=3.7, help='每秒汉字数，默认 3.7')
    ap.add_argument('--eng', type=float, default=0.4, help='每个英文词的秒数，默认 0.4')
    ap.add_argument('--max-sub', type=int, default=16, help='单条字幕最多汉字数')
    a = ap.parse_args()

    s = open(a.path, encoding='utf-8').read()
    shot_re = r'(?m)^\| (\d+-\d+) \| ([\d.]+) 秒 \|[^|]+\|[^|]+\| ([^|]+) \|'
    probs, scenes, acc, c_all, e_all, vo_by_scene = [], [], 0.0, 0, 0, []
    for no, title, body in re.findall(r'(?ms)^## (\d\d)｜([^\n]+)\n(.*?)(?=^## |\Z)', s):
        cs = cv = 0.0
        n = 0
        lines = []
        for shot, dur, vo in re.findall(shot_re, body):
            dur = float(dur)
            vo = vo.strip()
            n += 1
            cs += dur
            if vo != '—':
                plain = re.sub(SPEAKERS, '', vo.replace('<br>', ''))
                c, e = han(plain), eng(plain)
                cv += c / a.rate + e * a.eng
                c_all += c
                e_all += e
                for seg in vo.split('<br>'):
                    k = han(re.sub('^' + SPEAKERS, '', seg))
                    if k > a.max_sub:
                        probs.append(f'{shot} 字幕 {k} 字，超过 {a.max_sub}：{seg}')
                lines.append(vo)
            if cv > cs + 0.3:
                probs.append(f'{shot} 旁白累计比画面累计多 {cv - cs:.1f} 秒')
        scenes.append((no, title, n, acc, acc + cs))
        acc += cs
        vo_by_scene.append((no, title, lines))

    total_n = sum(x[2] for x in scenes)
    v1 = acc - (c_all / a.rate - c_all / 4.0)
    for no, title, n, st, en in scenes:
        print(f'{no} {n:>2} 镜 {en - st:5.1f}s  {mmss(st)}–{mmss(en)}  {title}')
    print(f'镜头 {total_n}  总长 {mmss(acc)} ({acc:.1f}s)  汉字 {c_all}  英文词 {e_all}  按每秒 4 字约 {mmss(v1)}')
    print('问题:', '无' if not probs else '')
    for p in probs:
        print('  -', p)

    if a.fill:
        s = re.sub(r'(?m)^(\| \d\d \| [^|]+ \| )\d+ \| [0-9:–]+ \|', r'\g<1>| |', s)
        for no, title, n, st, en in scenes:
            s = re.sub(rf'(\| {no} \| [^|]+ \| )\| \|', rf'\g<1>{n} | {mmss(st)}–{mmss(en)} |', s, count=1)
        s = re.sub(r'\n合计 \d+ 个镜头[^\n]+\n', '\n', s)
        silent = acc - c_all / a.rate - e_all * a.eng
        s = s.replace('\n## 音乐走向',
                      f'\n合计 {total_n} 个镜头，约 {mmss(acc)}；旁白和台词共 {c_all} 个汉字。'
                      f'按每秒 4 字的语速念，约 {mmss(v1)}。无旁白的时间约 {silent:.0f} 秒。\n\n## 音乐走向', 1)
        if '{VO_FULLTEXT}' in s:
            out = []
            for no, title, lines in vo_by_scene:
                paras, cur = [], ''
                for l in lines:
                    for seg in l.split('<br>'):
                        m = re.match('^' + SPEAKERS + '(.*)$', seg)
                        if m:
                            if cur:
                                paras.append(cur)
                                cur = ''
                            paras.append(f'{m.group(1)}：{m.group(2)}')
                        else:
                            cur += seg
                            if re.search(r'[。？！]$', seg):
                                paras.append(cur)
                                cur = ''
                if cur:
                    paras.append(cur)
                out.append(f'**{no}｜{title}**\n\n' + '\n\n'.join(paras))
            s = s.replace('{VO_FULLTEXT}', '\n\n'.join(out))
        open(a.path, 'w', encoding='utf-8').write(s)
        print('已回填:', a.path)
    return 1 if probs else 0


if __name__ == '__main__':
    sys.exit(main())
