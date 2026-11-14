#!/usr/bin/env python3
"""Render a smooth brass snake gliding over your real GitHub contribution graph.

Usage:
    make_snake.py calendar.json assets/snake.svg    # real data (output of the GraphQL query in snake.yml)
    make_snake.py --empty assets/snake.svg          # placeholder: empty graph, no data
Standard library only.
"""
import datetime as dt
import json
import math
import sys

BR, BRL, BRD = "#c9a46a", "#e6c58a", "#5c4a30"
TXT, MUT, BG, BD = "#e6edf3", "#8b949e", "#0d1117", "#30363d"
LEVELS = {"NONE": "#161b22", "FIRST_QUARTILE": "#4b3b22", "SECOND_QUARTILE": "#7d6339",
          "THIRD_QUARTILE": "#b5914f", "FOURTH_QUARTILE": "#e6c58a"}
LEGEND = list(LEVELS.values())
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def lerp(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(3))


def load_weeks(path):
    """-> (list of weeks; each week = list of (weekday 0..6, date, level)), total or None"""
    if path == "--empty":
        end = dt.date.today()
        start = end - dt.timedelta(days=364)
        start -= dt.timedelta(days=(start.weekday() + 1) % 7)          # back to a Sunday
        weeks, d = [], start
        while d <= end:
            week = []
            for k in range(7):
                if d <= end:
                    week.append(((d.weekday() + 1) % 7, d, "NONE"))
                d += dt.timedelta(days=1)
            weeks.append(week)
        return weeks, None
    data = json.load(open(path, encoding="utf-8"))
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        week = []
        for day in w["contributionDays"]:
            d = dt.date.fromisoformat(day["date"])
            level = day.get("contributionLevel") or ("NONE" if day["contributionCount"] == 0 else "FIRST_QUARTILE")
            week.append((day.get("weekday", (d.weekday() + 1) % 7), d, level))
        weeks.append(week)
    return weeks, cal.get("totalContributions")


def render(weeks, total):
    cols = len(weeks)
    size = 13.0
    pitch = min(17.5, (1000 - 80 - size) / (cols - 1))
    gw = (cols - 1) * pitch + size
    x0 = (1000 - gw) / 2
    y0 = 42.0
    gh = 6 * pitch + size
    H = int(y0 + gh + 36)

    cy_mid = y0 + gh / 2
    amp, per, ph = gh / 2 * 0.80, 250.0, 0.6
    ypath = lambda x: cy_mid + amp * math.sin(2 * math.pi * x / per + ph)
    xs = list(range(int(x0 - 70), int(x0 + gw + 74), 4))
    pts = [(x, ypath(x)) for x in xs]
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[i - 1], pts[i]))
    L = cum[-1]
    route = "M" + " L".join(f"{x} {y:.1f}" for x, y in pts)
    s_at = lambda x: cum[min(range(len(xs)), key=lambda k: abs(xs[k] - x))]
    T = 20.0
    MOVE = 0.8 * T
    speed = L / MOVE
    N, STEP = 120, 3.0
    dstep = STEP / speed

    cells, months, last_label_col = [], [], -9
    for c, week in enumerate(weeks):
        x = x0 + c * pitch
        first = week[0][1]
        if first.month != (weeks[c - 1][0][1].month if c else None) and c - last_label_col >= 3 and c <= cols - 3:
            months.append(f'<text class="sans" x="{x:.1f}" y="{y0 - 12:.1f}" font-size="12" fill="{MUT}">{MONTHS[first.month - 1]}</text>')
            last_label_col = c
        for wd, d, level in week:
            y = y0 + wd * pitch
            col = LEVELS.get(level, LEVELS["NONE"])
            cx, cy = x + size / 2, y + size / 2
            tip = f'<title>{d.isoformat()}</title>'
            if abs(cy - ypath(cx)) <= 16:
                delay = s_at(cx) / L * MOVE
                cells.append(f'<rect class="c" x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" rx="2.5" fill="{col}" '
                             f'style="--c:{col};animation-delay:{delay:.2f}s">{tip}</rect>')
            else:
                cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" rx="2.5" fill="{col}">{tip}</rect>')

    def motion(begin, extra=""):
        return (f'<animateMotion dur="{T}s" begin="{begin:.3f}s" repeatCount="indefinite" calcMode="linear" '
                f'keyPoints="0;1;1" keyTimes="0;0.8;1" {extra}><mpath href="#route" xlink:href="#route"/></animateMotion>')

    body = []
    for i in range(N - 1, 0, -1):
        t = i / N
        r = 1.5 + 6.2 * (1 - t) ** 0.55
        col = lerp(BRL, BRD, t ** 0.8)
        if (i // 4) % 2 == 0:
            col = lerp(col, "#ffffff", 0.07)
        b = i * dstep
        body.append(f'<circle r="{r:.2f}" fill="{col}" visibility="hidden"><set attributeName="visibility" to="visible" begin="{b:.3f}s"/>{motion(b)}</circle>')
    head = (f'<g visibility="hidden"><set attributeName="visibility" to="visible" begin="0s"/>{motion(0, "rotate=" + chr(34) + "auto" + chr(34))}'
            f'<ellipse rx="10" ry="7.4" fill="{BRL}"/>'
            f'<circle cx="3" cy="-3.5" r="1.7" fill="{BG}"/><circle cx="3" cy="3.5" r="1.7" fill="{BG}"/>'
            f'<path d="M9.5 0 L16 0 M16 0 L19.3 -2.2 M16 0 L19.3 2.2" stroke="#e5484d" stroke-width="1.2" fill="none" stroke-linecap="round">'
            f'<animate attributeName="opacity" values="0;0;1;1" keyTimes="0;0.55;0.56;1" dur="1.4s" repeatCount="indefinite"/></path></g>')

    foot_y = y0 + gh + 23
    foot = []
    if total is not None:
        foot.append(f'<text class="sans" x="{x0:.1f}" y="{foot_y:.1f}" font-size="13" fill="{MUT}">{total:,} contributions in the last year</text>')
    lx = x0 + gw - 148
    foot.append(f'<text class="sans" x="{lx:.1f}" y="{foot_y:.1f}" font-size="12" fill="{MUT}">Less</text>')
    for k, col in enumerate(LEGEND):
        foot.append(f'<rect x="{lx + 34 + k * 15:.1f}" y="{foot_y - 10:.1f}" width="11" height="11" rx="2.5" fill="{col}"/>')
    foot.append(f'<text class="sans" x="{lx + 34 + 5 * 15 + 5:.1f}" y="{foot_y:.1f}" font-size="12" fill="{MUT}">More</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1000 {H}" role="img" aria-labelledby="t d">
  <title id="t">Contribution graph with a snake</title>
  <desc id="d">My GitHub contribution graph for the last year. A small brass snake glides across it and lights up the squares it passes.</desc>
  <style>
    .sans {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .c {{ animation: glow {T}s linear infinite; }}
    @keyframes glow {{ 0% {{ fill: #fff3d6; }} 17% {{ fill: var(--c); }} 100% {{ fill: var(--c); }} }}
    @media (prefers-reduced-motion: reduce) {{ .c {{ animation: none; }} }}
  </style>
  <defs><path id="route" d="{route}"/></defs>
  <rect x=".5" y=".5" width="999" height="{H - 1}" rx="14" fill="{BG}" stroke="{BD}"/>
  {"".join(months)}
  <g>{"".join(cells)}</g>
  <g>{"".join(foot)}</g>
  <g>{"".join(body)}{head}</g>
</svg>
'''


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    weeks, total = load_weeks(sys.argv[1])
    out = render(weeks, total)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print(f"wrote {sys.argv[2]}: {len(weeks)} weeks, {len(out) // 1024} KB")
