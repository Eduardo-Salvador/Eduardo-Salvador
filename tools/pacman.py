"""Renders the contribution calendar as a Pac-Man board (pacman_dark.svg / pacman_light.svg).

Pac-Man walks the calendar week by week (down one column, up the next), eating
each day as he passes; three ghosts follow a few days behind. Pure SVG/SMIL,
no scripts, so GitHub renders it inside the README.

Usage: GITHUB_TOKEN=... python tools/pacman.py
"""
import datetime as dt
import json
import os
import urllib.request

GH_USER = "Eduardo-Salvador"

BG, FG = (0x16, 0x1B, 0x22), (0xC9, 0xD1, 0xD9)
TEXT, DIM = "#c9d1d9", "#8b949e"
PAC = "#ffa657"
GHOSTS = ["#ff7b72", "#79c0ff", "#d2a8ff"]
LEVEL_MIX = (0.10, 0.30, 0.50, 0.72, 1.0)
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

W = 985
MARGIN, LABEL_COL = 18, 34
CELL, PITCH = 13, 17
TOP = 58                    # header + month labels
STEP = 0.045                # seconds per day
INTRO, OUTRO = 1.2, 1.8
GHOST_LAG = (6, 11, 16)     # days behind Pac-Man


def calendar():
    q = f'{{user(login:"{GH_USER}"){{contributionsCollection{{contributionCalendar{{totalContributions weeks{{contributionDays{{date weekday contributionLevel}}}}}}}}}}}}'
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def mix(t):
    return "#%02x%02x%02x" % tuple(round(b + (f - b) * t) for b, f in zip(BG, FG))


def cell_xy(w, d):
    return MARGIN + LABEL_COL + w * PITCH, TOP + d * PITCH


def pacman_paths(r):
    # open and closed mouth, facing right (rotated by the group)
    open_ = f"M0,0 L{r},{-r*0.62} A{r},{r} 0 1,0 {r},{r*0.62} Z"
    shut = f"M0,0 L{r},{-r*0.12} A{r},{r} 0 1,0 {r},{r*0.12} Z"
    return open_, shut


def ghost_path(r):
    # rounded head, wavy skirt, centred on 0,0
    return (f"M{-r},{r} L{-r},0 A{r},{r} 0 0,1 {r},0 L{r},{r} "
            f"L{r*0.5},{r*0.6} L0,{r} L{-r*0.5},{r*0.6} Z")


def build():
    total, weeks = calendar()
    order = []          # (week, weekday) in Pac-Man's walking order
    for w, wk in enumerate(weeks):
        days = sorted(wk["contributionDays"], key=lambda d: d["weekday"])
        if w % 2:
            days = days[::-1]
        order += [(w, d["weekday"]) for d in days]
    n = len(order)
    T = INTRO + n * STEP + OUTRO
    kt = lambda t: f"{min(max(t / T, 0), 1):.5f}"

    H = TOP + 7 * PITCH + 38
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="ConsolasFallback,Consolas,monospace">',
         f'<rect width="{W}" height="{H}" rx="12" fill="{mix(0)}"/>',
         f'<text x="{MARGIN}" y="26" fill="{TEXT}" font-size="14">{total:,} contributions in the last year</text>']

    # month labels
    last = None
    for w, wk in enumerate(weeks):
        m = dt.date.fromisoformat(wk["contributionDays"][0]["date"]).strftime("%b")
        if m != last and w < len(weeks) - 2:
            o.append(f'<text x="{cell_xy(w, 0)[0]}" y="{TOP - 8}" fill="{DIM}" font-size="11">{m}</text>')
        last = m
    for d, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        o.append(f'<text x="{MARGIN}" y="{cell_xy(0, d)[1] + 10}" fill="{DIM}" font-size="11">{lab}</text>')

    # days: each one vanishes when Pac-Man reaches it and comes back at the reset
    level = {}
    for w, wk in enumerate(weeks):
        for day in wk["contributionDays"]:
            level[(w, day["weekday"])] = LEVELS.get(day["contributionLevel"], 0)
    for i, (w, d) in enumerate(order):
        x, y = cell_xy(w, d)
        t = INTRO + i * STEP + STEP * 0.5
        o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{mix(LEVEL_MIX[level[(w, d)]])}">'
                 f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{kt(t)};{kt(t + 0.001)};1" dur="{T:.2f}s" repeatCount="indefinite"/></rect>')

    # legend
    lx = W - MARGIN - 5 * PITCH - 40
    ly = TOP + 7 * PITCH + 14
    o.append(f'<text x="{lx - 34}" y="{ly + 10}" fill="{DIM}" font-size="11">Less</text>')
    for k, t in enumerate(LEVEL_MIX):
        o.append(f'<rect x="{lx + k * PITCH}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{mix(t)}"/>')
    o.append(f'<text x="{lx + 5 * PITCH + 4}" y="{ly + 10}" fill="{DIM}" font-size="11">More</text>')

    # movement: one translate keyframe per day, shared by Pac-Man and (delayed) ghosts
    centers = [(cell_xy(w, d)[0] + CELL / 2, cell_xy(w, d)[1] + CELL / 2) for w, d in order]

    def motion(lag):
        pts = [centers[0]] * (lag + 1) + centers + [centers[-1]]
        times = [0, INTRO] + [INTRO + i * STEP for i in range(1, len(pts) - 2)] + [T]
        vals = ";".join(f"{x:.1f},{y:.1f}" for x, y in pts[:len(times)])
        keys = ";".join(kt(t) for t in times)
        return f'<animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{keys}" dur="{T:.2f}s" repeatCount="indefinite"/>'

    # Pac-Man faces down on even weeks, up on odd ones, right while changing column
    rots, rkeys = [], []
    for i, (w, d) in enumerate(order):
        nxt = order[i + 1] if i + 1 < n else (w, d)
        ang = 0 if nxt[0] != w else (90 if w % 2 == 0 else -90)
        rots.append(str(ang)); rkeys.append(kt(INTRO + i * STEP))
    rkeys[0] = "0"
    rot = (f'<animateTransform attributeName="transform" type="rotate" values="{";".join(rots)}" keyTimes="{";".join(rkeys)}" '
           f'calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>')

    for g, lag in reversed(list(zip(GHOSTS, GHOST_LAG))):
        o.append(f'<g>{motion(lag)}<path d="{ghost_path(6.5)}" fill="{g}"/>'
                 f'<circle cx="-2.4" cy="-0.5" r="1.6" fill="#fff"/><circle cx="2.4" cy="-0.5" r="1.6" fill="#fff"/></g>')

    op, sh = pacman_paths(8)
    o.append(f'<g>{motion(0)}<g>{rot}'
             f'<path d="{op}" fill="{PAC}"><animate attributeName="d" values="{op};{sh};{op}" dur="0.24s" repeatCount="indefinite"/></path>'
             f'</g></g>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    svg = build()
    for theme in ("dark", "light"):   # light uses the same dark card, like the profile card
        with open(f"pacman_{theme}.svg", "w", encoding="utf-8") as f:
            f.write(svg)
    print("ok")
