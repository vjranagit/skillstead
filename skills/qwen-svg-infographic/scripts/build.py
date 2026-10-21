"""Content JSON -> lane infographic. Qwen writes content only; this script owns layout,
routing and measurement, and fails with a one-line fix hint instead of shipping overlaps."""
import json, os, pathlib, shutil, struct, subprocess, sys
from xml.sax.saxutils import escape
from PIL import ImageFont

root = pathlib.Path(__file__).resolve().parents[3]
skill = root / 'skills/svg-infographic'
FONTS = pathlib.Path('/usr/share/fonts/truetype/dejavu')
ACCENT = ['#2E6DA4', '#B45309', '#047857', '#7C3AED']
TINT = ['#EAF1F8', '#FBF1E6', '#E7F4EE', '#F1ECFB']
W, M, STRIP, TRACK, PILL_H = 1360, 48, 44, 28, 22


class Fix(Exception):
    pass


_fonts = {}
def width(text, size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(str(FONTS / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)
    return _fonts[key].getlength(text)


def fit(what, text, size, bold, room, max_lines):
    lines, cur = [], ''
    for word in str(text).split():
        nxt = f'{cur} {word}'.strip()
        if cur and width(nxt, size, bold) > room:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    lines += [cur] if cur else []
    if not lines:
        raise Fix(f'{what} is empty; write it')
    wide = [l for l in lines if width(l, size, bold) > room]
    if wide:
        raise Fix(f'{what}: "{wide[0]}" is wider than {room:.0f}px; abbreviate that word')
    if len(lines) > max_lines:
        excess = sum(width(l, size, bold) for l in lines[max_lines:])
        raise Fix(f'{what} needs {len(lines)} lines (max {max_lines}); cut about {int(excess / (size * .6)) + 3} characters')
    return lines


def hits(r, s):  # rect r=(x0,y0,x1,y1) vs segment or rect s
    return min(r[2], max(s[0], s[2])) > max(r[0], min(s[0], s[2])) and min(r[3], max(s[1], s[3])) > max(r[1], min(s[1], s[3]))


def build(data):
    groups, links = data['groups'], data['links']
    if not 1 <= len(groups) <= 4 or not all(1 <= len(g['parts']) <= 4 for g in groups):
        raise Fix('use 1-4 groups with 1-4 parts each; merge minor parts')
    pos, part = {}, {}
    for lane, g in enumerate(groups):
        for col, p in enumerate(g['parts']):
            if p['id'] in pos:
                raise Fix(f'duplicate part id "{p["id"]}"; make ids unique')
            pos[p['id']], part[p['id']] = (lane, col), p
    if not 1 <= len(links) <= 16:
        raise Fix('use 1-16 links; keep the relationships that matter')
    seen = set()
    for l in links:
        if l['from'] not in pos or l['to'] not in pos or l['from'] == l['to']:
            raise Fix(f'link {l["from"]}->{l["to"]} must join two different existing part ids')
        if (l['from'], l['to']) in seen:
            raise Fix(f'duplicate link {l["from"]}->{l["to"]}; keep one')
        seen.add((l['from'], l['to']))
    for pid in pos:
        if len(pos) > 1 and not any(pid in (l['from'], l['to']) for l in links):
            raise Fix(f'part "{pid}" has no link; link it to the part it acts on, or drop it')

    ncol = max(len(g['parts']) for g in groups)
    nlane = len(groups)
    for l in links:
        (la, ca), (lb, cb) = pos[l['from']], pos[l['to']]
        l['straight'] = la == lb and cb == ca + 1
        l['tag'] = l.get('label', '').strip()
        l['tag_w'] = width(l['tag'], 14, True) + 16 if l['tag'] else 0
    gap = max([64] + [l['tag_w'] + 56 for l in links if l['straight'] and l['tag']])
    if gap > 136:
        raise Fix('label on a side-by-side link is too long; shorten it to ~9 characters or drop it')

    # Links spanning 2+ lanes drop through a column gap (boundary b sits left of column b; ncol = right strip).
    vtracks = {}
    for l in links:
        (la, ca), (lb, cb) = pos[l['from']], pos[l['to']]
        if abs(la - lb) < 2:
            continue
        lo, hi = sorted((la, lb))
        blocked = {pos[k['from']][1] + 1 for k in links if k['straight'] and k['tag'] and lo < pos[k['from']][0] < hi}
        options = sorted(range(1, ncol + 1), key=lambda b: (abs(b - (ca + cb + 1) / 2), b))
        b = next(b for b in options if b not in blocked)  # the right strip is never blocked
        used = vtracks.setdefault(b, [])
        k = next(i for i in range(len(used) + 1) if i == len(used) or all(not (lo < h and l2 < hi) for l2, h in used[i]))
        if k == len(used):
            used.append([])
        used[k].append((lo, hi))
        l['vgap'], l['vtrack'] = b, k
    gap = max(gap, max([0] + [20 + 16 * len(t) for b, t in vtracks.items() if b < ncol]))
    right = 16 + 16 * len(vtracks[ncol]) if ncol in vtracks else 14
    x0 = M + STRIP + 10
    card_w = (W - M - right - x0 - (ncol - 1) * gap) / ncol
    if card_w < 190:
        raise Fix('cards too narrow; use at most 3 parts per group or shorter side-by-side link labels')
    cx = lambda c: x0 + c * (card_w + gap)
    for l in links:
        if 'vgap' in l:
            n = len(vtracks[l['vgap']])
            mid = cx(l['vgap']) - gap / 2 if l['vgap'] < ncol else W - M - right / 2
            l['vx'] = mid + (l['vtrack'] - (n - 1) / 2) * 16

    # Measured text: titles, card text, lane names, takeaway.
    title = fit('title', data['title'], 38, True, W - 2 * M, 1)
    subtitle = fit('subtitle', data['subtitle'], 20, False, W - 2 * M, 2)
    takeaway = fit('takeaway', data['takeaway'], 20, True, W - 2 * M, 2)
    inner = card_w - 28
    for pid, p in part.items():
        p['lines'] = fit(f'part "{pid}" label', p['label'], 19, True, inner, 2)
        p['detail_lines'] = fit(f'part "{pid}" detail', p['detail'], 16, False, inner, 3)
    nl = max(len(p['lines']) for p in part.values())
    nd = max(len(p['detail_lines']) for p in part.values())
    card_h = 16 + nl * 24 + 8 + nd * 21 + 14
    band_h = card_h + 36
    for i, g in enumerate(groups):
        fit(f'group {i + 1} name', g['name'], 15, True, band_h - 16, 1)

    # Ports: each routed end gets its own x on the card's top/bottom edge.
    ends = {}
    for i, l in enumerate(links):
        if l['straight']:
            continue
        (la, ca), (lb, cb) = pos[l['from']], pos[l['to']]
        l['side_from'] = 'top' if la > lb else 'bottom'
        l['side_to'] = 'top' if la < lb else 'bottom'
        ends.setdefault((l['from'], l['side_from']), []).append((cx(cb), i, 'px_from'))
        ends.setdefault((l['to'], l['side_to']), []).append((cx(ca), i, 'px_to'))
    for (pid, side), lst in ends.items():
        for k, (_, i, key) in enumerate(sorted(lst)):
            links[i][key] = cx(pos[pid][1]) + card_w * (k + 1) / (len(lst) + 1) + (10 if side == 'top' else 0)

    # Horizontal runs live in gutter g (below lane g); give overlapping runs separate tracks.
    runs = {}
    for i, l in enumerate(links):
        if l['straight']:
            continue
        (la, _), (lb, _) = pos[l['from']], pos[l['to']]
        if 'vgap' in l:
            g1, g2 = (la, lb - 1) if la < lb else (la - 1, lb)
            l['runs'] = [(g1, l['px_from'], l['vx']), (g2, l['vx'], l['px_to'])]
        else:
            l['runs'] = [(min(la, lb), l['px_from'], l['px_to'])]
        for k, (g, a, b) in enumerate(l['runs']):
            pad = l['tag_w'] / 2 + 8 if l['tag'] else 8
            runs.setdefault(g, []).append((min(a, b) - pad, max(a, b) + pad, i, k))
    tracks = {}
    for g, lst in runs.items():
        ends_at = []
        for a, b, i, k in sorted(lst):
            t = next((t for t, e in enumerate(ends_at) if e < a), len(ends_at))
            ends_at[t:t + 1] = [b]
            links[i].setdefault('track', {})[k] = t
        tracks[g] = len(ends_at)

    # Vertical placement.
    y = M + 38
    title_y, sub_y = y, y + 40
    y = sub_y + 26 * (len(subtitle) - 1) + 30
    band_top, gutter_top = [], []
    for g in range(nlane):
        band_top.append(y)
        y += band_h
        gutter_top.append(y)
        y += 16 * 2 + TRACK * (tracks[g] - 1) if tracks.get(g) else 24
    take_y = y + 26
    height = int(take_y + 28 * (len(takeaway) - 1) + M)
    card = {pid: (cx(c), band_top[lane] + 18, cx(c) + card_w, band_top[lane] + 18 + card_h) for pid, (lane, c) in pos.items()}

    for l in links:
        s, t = card[l['from']], card[l['to']]
        if l['straight']:
            my = (s[1] + s[3]) / 2
            l['pts'] = [(s[2], my), (t[0], my)]
            continue
        ty = [gutter_top[g] + 16 + TRACK * l['track'][k] for k, (g, _, _) in enumerate(l['runs'])]
        sy = s[3] if l['side_from'] == 'bottom' else s[1]
        ey = t[3] if l['side_to'] == 'bottom' else t[1]
        pts = [(l['px_from'], sy), (l['px_from'], ty[0])]
        if 'vgap' in l:
            pts += [(l['vx'], ty[0]), (l['vx'], ty[1])]
        l['pts'] = pts + [(l['px_to'], ty[-1]), (l['px_to'], ey)]
    for l in links:
        l['segs'] = [(a[0], a[1], b[0], b[1]) for a, b in zip(l['pts'], l['pts'][1:]) if a != b]

    # Checks the renderer can prove: no route through a card, no shared line, labels on clear ground.
    boxes = list(card.values())
    for i, l in enumerate(links):
        for sg in l['segs']:
            if any(hits((c[0] + 1, c[1] + 1, c[2] - 1, c[3] - 1), sg) for c in boxes):
                raise Fix(f'link {l["from"]}->{l["to"]} cannot avoid a card; reorder parts so linked parts sit in nearer columns')
            for o in links[i + 1:]:
                for so in o['segs']:
                    same_h = sg[1] == sg[3] == so[1] == so[3] and min(max(sg[0], sg[2]), max(so[0], so[2])) - max(min(sg[0], sg[2]), min(so[0], so[2])) > 1
                    same_v = sg[0] == sg[2] == so[0] == so[2] and min(max(sg[1], sg[3]), max(so[1], so[3])) - max(min(sg[1], sg[3]), min(so[1], so[3])) > 1
                    if same_h or same_v:
                        raise Fix(f'links {l["from"]}->{l["to"]} and {o["from"]}->{o["to"]} share a line; reorder parts in their group')
    strips = [(M, band_top[g], M + STRIP, band_top[g] + band_h) for g in range(nlane)]
    pills = []
    for l in links:
        if not l['tag']:
            continue
        spots = []
        for sg in sorted((s for s in l['segs'] if s[1] == s[3]), key=lambda s: -abs(s[2] - s[0])):
            spots += [(sg[0] + f * (sg[2] - sg[0]), sg[1]) for f in ((.5,) if l['straight'] else (.5, .35, .65, .2, .8, 0, 1))]
        others = [sg for o in links if o is not l for sg in o['segs']]
        for px, py in spots:
            r = (px - l['tag_w'] / 2, py - PILL_H / 2, px + l['tag_w'] / 2, py + PILL_H / 2)
            if r[0] > M and r[2] < W - M and not any(hits(r, b) for b in boxes + strips + pills + others):
                pills.append(r)
                l['pill'] = r
                break
        else:
            raise Fix(f'label "{l["tag"]}" on link {l["from"]}->{l["to"]} has no clear spot; shorten or drop it')

    # SVG.
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" font-family="DejaVu Sans, sans-serif">',
           f'<title>{escape(data["title"])}</title><desc>{escape(data["takeaway"])}</desc><defs>']
    out += [f'<marker id="a{i}" markerUnits="userSpaceOnUse" markerWidth="10.5" markerHeight="10.5" viewBox="0 0 10 10" refX="10" refY="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>' for i, c in enumerate(ACCENT)]
    out.append(f'</defs><rect width="100%" height="100%" fill="#F7F7F5"/><text x="{M}" y="{title_y}" font-size="38" font-weight="700" fill="#193C5A">{escape(title[0])}</text>')
    out += [f'<text x="{M}" y="{sub_y + 26 * j}" font-size="20" fill="#475569">{escape(s)}</text>' for j, s in enumerate(subtitle)]
    for g, grp in enumerate(groups):
        bt, mid = band_top[g], band_top[g] + band_h / 2
        out.append(f'<rect x="{M}" y="{bt}" width="{W - 2 * M}" height="{band_h}" rx="12" fill="{TINT[g]}"/><text x="{M + 28}" y="{mid}" transform="rotate(-90 {M + 28} {mid})" text-anchor="middle" font-size="15" font-weight="700" fill="{ACCENT[g]}">{escape(grp["name"])}</text>')
    for pid, (x, yy, x2, y2) in card.items():
        p, g = part[pid], pos[pid][0]
        out.append(f'<rect x="{x:.1f}" y="{yy}" width="{card_w:.1f}" height="{card_h}" rx="10" fill="#FFFFFF" stroke="{ACCENT[g]}" stroke-width="2"/>')
        out += [f'<text x="{x + 14:.1f}" y="{yy + 34 + 24 * j}" font-size="19" font-weight="700" fill="#193C5A">{escape(s)}</text>' for j, s in enumerate(p['lines'])]
        dy = yy + 16 + 24 * len(p['lines']) + 8 + 16
        out += [f'<text x="{x + 14:.1f}" y="{dy + 21 * j}" font-size="16" fill="#475569">{escape(s)}</text>' for j, s in enumerate(p['detail_lines'])]
    for l in links:
        g = pos[l['from']][0]
        d = 'M' + 'L'.join(f'{x:.1f} {yy:.1f}' for x, yy in l['pts'])
        out.append(f'<path d="{d}" fill="none" stroke="{ACCENT[g]}" stroke-width="3" stroke-linejoin="round" marker-end="url(#a{g})"/>')
    for l in links:
        if 'pill' in l:
            r, g = l['pill'], pos[l['from']][0]
            out.append(f'<rect x="{r[0]:.1f}" y="{r[1]:.1f}" width="{r[2] - r[0]:.1f}" height="{PILL_H}" rx="11" fill="#FFFFFF" stroke="{ACCENT[g]}" stroke-width="1.2"/><text x="{(r[0] + r[2]) / 2:.1f}" y="{r[1] + 16:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="{ACCENT[g]}">{escape(l["tag"])}</text>')
    out += [f'<text x="{M}" y="{take_y + 28 * j}" font-size="20" font-weight="700" fill="#193C5A">{escape(s)}</text>' for j, s in enumerate(takeaway)]
    out.append('</svg>')
    return ''.join(out)


try:
    src_json = pathlib.Path(sys.argv[1]).resolve()
    try:
        svg = build(json.loads(src_json.read_text()))
    except (KeyError, TypeError, AttributeError) as e:
        raise Fix(f'content is missing field {e}; restore the template keys')
    out = pathlib.Path(sys.argv[2]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if src_json != out / 'content.json':
        shutil.copyfile(src_json, out / 'content.json')
    browser = os.environ.get('SVG_INFOGRAPHIC_BROWSER') or str(pathlib.Path.home() / '.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell')
    src, png = out / 'infographic.svg', out / 'infographic.png'
    src.write_text(svg)
    r = subprocess.run(['env', '-u', 'DISPLAY', '-u', 'WAYLAND_DISPLAY', 'SVG_INFOGRAPHIC_BROWSER=' + browser, 'node', str(skill / 'scripts/render.mjs'), str(src), str(png)], capture_output=True, text=True)
    if r.returncode:
        log = (r.stderr + r.stdout).strip().splitlines()
        raise RuntimeError('render failed: ' + ' | '.join([ln.strip() for ln in log if 'ERROR' in ln][:3] or log[-3:]))
    raw = png.read_bytes()
    pw, ph = struct.unpack('>II', raw[16:24])
    assert pw > 0 and ph > 0 and any(raw[33:])
    print(json.dumps({'ok': True, 'png': str(png), 'svg': str(src), 'width': pw, 'height': ph}))
except Fix as e:
    print(json.dumps({'ok': False, 'fix': str(e)}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({'ok': False, 'error': str(e)}))
    sys.exit(1)
