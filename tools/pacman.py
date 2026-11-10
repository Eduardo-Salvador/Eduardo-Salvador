"""Renders the contribution calendar as a Pac-Man board (pacman_dark.svg / pacman_light.svg).

Pac-Man wanders the calendar like in the arcade: he always heads for a nearby
uneaten day (ties broken at random), eating every day that had contributions,
while three little pixel Claudes follow a few steps behind. Pure SVG/SMIL,
no scripts, so GitHub renders it inside the README.

Usage: GITHUB_TOKEN=... python tools/pacman.py
"""
import datetime as dt
import json
import os
import random
from collections import deque
import urllib.request

GH_USER = "Eduardo-Salvador"

BG, FG = (0x16, 0x1B, 0x22), (0xC9, 0xD1, 0xD9)
TEXT, DIM = "#c9d1d9", "#8b949e"
PAC = "#ffd33d"
ORANGE = (0xFF, 0x8C, 0x42)

LEVEL_MIX = (0.10, 0.30, 0.55, 0.80, 1.0)   # level 0 is grey, 1-4 go from dark to bright orange
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

W = 985
MARGIN, LABEL_COL = 18, 34
CELL, PITCH = 13, 17
TOP = 58                    # header + month labels
STEP = 0.11                 # seconds per step
INTRO, OUTRO = 1.2, 0.4      # restarts right after Pac-Man finishes
GHOST_LAG = (5, 10, 15, 20)  # steps behind Pac-Man


def calendar():
    q = f'{{user(login:"{GH_USER}"){{contributionsCollection{{contributionCalendar{{totalContributions weeks{{contributionDays{{date weekday contributionLevel contributionCount}}}}}}}}}}}}'
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def mix(t, to=FG):
    return "#%02x%02x%02x" % tuple(round(b + (f - b) * t) for b, f in zip(BG, to))


def level_color(lv):
    return mix(LEVEL_MIX[0]) if lv == 0 else mix(LEVEL_MIX[lv], ORANGE)


def cell_xy(w, d):
    return MARGIN + LABEL_COL + w * PITCH, TOP + d * PITCH


def pacman_paths(r):
    # open and closed mouth, facing right (rotated by the group)
    open_ = f"M0,0 L{r},{-r*0.62} A{r},{r} 0 1,0 {r},{r*0.62} Z"
    shut = f"M0,0 L{r},{-r*0.12} A{r},{r} 0 1,0 {r},{r*0.12} Z"
    return open_, shut


# pixel "ghosts": AI and Java mascots. Each char is a colour, "." is transparent.
SPRITES = {
    "claude": ([
        ".#######.",
        ".#o###o#.",
        "#########",
        ".#######.",
        ".#.#.#.#.",
    ], {"#": "#d97757", "o": "#161b22"}),
    "openai": ([
        "...www...",
        ".ww...ww.",
        "w..www..w",
        "w.w...w.w",
        "w..www..w",
        ".ww...ww.",
        "...www...",
    ], {"w": "#f0f6fc"}),
    "deepseek": ([
        "......b..",
        ".bbbb..b.",
        "bbbbbbbb.",
        "bwbbbbbbb",
        "bbbbbbbb.",
        ".lllll...",
    ], {"b": "#4d6bfe", "w": "#f0f6fc", "l": "#8fa4ff"}),
    "duke": ([
        "...k...",
        "..kkk..",
        ".kwwwk.",
        ".kwrwk.",
        "kkwwwkk",
        ".kkkkk.",
        ".k...k.",
    ], {"k": "#6e7681", "w": "#f0f6fc", "r": "#e11d2e"}),
}
U = 2.0             # px per sprite pixel


def sprite(name):
    rows, colors = SPRITES[name]
    h, w = len(rows), len(rows[0])
    out = []
    for ch, color in colors.items():
        d = "".join(f"M{(x - w / 2) * U:.1f},{(y - h / 2) * U:.1f}h{U}v{U}h{-U}z"
                    for y, row in enumerate(rows) for x, c in enumerate(row) if c == ch)
        out.append(f'<path d="{d}" fill="{color}" shape-rendering="crispEdges"/>')
    return "".join(out)


def walk(cells, food, seed):
    """Arcade-like route: BFS to the nearest uneaten food, random among ties."""
    rnd = random.Random(seed)
    start = min(cells)
    path, left = [start], set(food) - {start}
    pos = start
    while left:
        prev, q, found = {pos: None}, deque([pos]), []
        while q and not found:
            for _ in range(len(q)):
                c = q.popleft()
                nb = [(c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)]
                rnd.shuffle(nb)
                for v in nb:
                    if v in cells and v not in prev:
                        prev[v] = c
                        q.append(v)
                        if v in left:
                            found.append(v)
        goal = rnd.choice(found)
        seg = []
        while goal != pos:
            seg.append(goal)
            goal = prev[goal]
        path += seg[::-1]
        pos = path[-1]
        left -= set(seg)
    return path


def build():
    total, weeks = calendar()
    exists = {(w, d["weekday"]) for w, wk in enumerate(weeks) for d in wk["contributionDays"]}
    level = {(w, d["weekday"]): LEVELS.get(d["contributionLevel"], 0) for w, wk in enumerate(weeks) for d in wk["contributionDays"]}
    food = [c for c in exists if level[c]]
    order = walk(exists, food, seed=dt.date.today().toordinal())   # new route every day
    n = len(order)
    eat = {}
    for i, c in enumerate(order):
        eat.setdefault(c, i)
    T = INTRO + n * STEP + OUTRO
    kt = lambda t: f"{min(max(t / T, 0), 1):.5f}"

    H = TOP + 7 * PITCH + 38
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="ConsolasFallback,Consolas,monospace">',
         f'<rect width="{W}" height="{H}" rx="12" fill="{mix(0)}"/>',
         ]

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
    for (w, d) in sorted(exists):
        x, y = cell_xy(w, d)
        lv = level[(w, d)]
        o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{mix(LEVEL_MIX[0])}"/>')
        if lv:  # only days with contributions are food
            t = INTRO + eat[(w, d)] * STEP + STEP * 0.5
            o.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{level_color(lv)}">'
                     f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{kt(t)};{kt(t + 0.001)};1" dur="{T:.2f}s" repeatCount="indefinite"/></rect>')

    # header counts up like an arcade score as each day is eaten
    count = {(w, d["weekday"]): d["contributionCount"] for w, wk in enumerate(weeks) for d in wk["contributionDays"]}
    events, acc = [(0.0, 0)], 0
    for cell in sorted((c for c in exists if count[c]), key=eat.get):
        acc += count[cell]
        events.append((INTRO + eat[cell] * STEP + STEP * 0.5, acc))
    for j, (t0, val) in enumerate(events):
        t1 = events[j + 1][0] if j + 1 < len(events) else T
        if j == 0:
            vis, keys = "1;0", f"0;{kt(t1)}"
        elif j + 1 == len(events):
            vis, keys = "0;1", f"0;{kt(t0)}"
        else:
            vis, keys = "0;1;0", f"0;{kt(t0)};{kt(t1)}"
        o.append(f'<text x="{MARGIN}" y="26" fill="{TEXT}" font-size="14" opacity="0">{val:,} contributions in the last year'
                 f'<animate attributeName="opacity" values="{vis}" keyTimes="{keys}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></text>')

    # legend
    lx = W - MARGIN - 5 * PITCH - 40
    ly = TOP + 7 * PITCH + 14
    o.append(f'<text x="{lx - 34}" y="{ly + 10}" fill="{DIM}" font-size="11">Less</text>')
    for k, t in enumerate(LEVEL_MIX):
        o.append(f'<rect x="{lx + k * PITCH}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{level_color(k)}"/>')
    o.append(f'<text x="{lx + 5 * PITCH + 4}" y="{ly + 10}" fill="{DIM}" font-size="11">More</text>')

    # movement: one translate keyframe per day, shared by Pac-Man and (delayed) ghosts
    centers = [(cell_xy(w, d)[0] + CELL / 2, cell_xy(w, d)[1] + CELL / 2) for w, d in order]

    def motion(lag):
        pts = [centers[0]] * (lag + 1) + centers
        times = [0, INTRO] + [INTRO + i * STEP for i in range(1, len(pts) - 1)]
        keep = [i for i, t in enumerate(times) if t < T]
        pts, times = [pts[i] for i in keep] + [pts[keep[-1]]], [times[i] for i in keep] + [T]
        vals = ";".join(f"{x:.1f},{y:.1f}" for x, y in pts[:len(times)])
        keys = ";".join(kt(t) for t in times)
        return f'<animateTransform attributeName="transform" type="translate" values="{vals}" keyTimes="{keys}" dur="{T:.2f}s" repeatCount="indefinite"/>'

    # Pac-Man faces the direction of his next step
    rots, rkeys, ang = [], [], 0
    for i, (w, d) in enumerate(order):
        nxt = order[i + 1] if i + 1 < n else (w, d)
        dx, dy = nxt[0] - w, nxt[1] - d
        ang = {(1, 0): 0, (-1, 0): 180, (0, 1): 90, (0, -1): -90}.get((dx, dy), ang)
        rots.append(str(ang)); rkeys.append(kt(INTRO + i * STEP))
    rkeys[0] = "0"
    rot = (f'<animateTransform attributeName="transform" type="rotate" values="{";".join(rots)}" keyTimes="{";".join(rkeys)}" '
           f'calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/>')

    for name, lag in reversed(list(zip(("claude", "openai", "deepseek", "duke"), GHOST_LAG))):
        o.append(f'<g>{motion(lag)}{sprite(name)}</g>')

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
