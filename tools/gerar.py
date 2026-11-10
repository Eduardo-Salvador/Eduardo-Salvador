# Gera dark_mode.svg / light_mode.svg no estilo "neofetch" (ASCII + infos)
# Uso local:   python tools/gerar.py
# No GitHub:   a Action roda todo dia, recalcula o Uptime e busca as stats.
import os, json, html, time, datetime, urllib.request
from PIL import Image, ImageOps, ImageFilter

FOTO = "assets/foto.png"
GH_USER = "Eduardo-Salvador"
NASCIMENTO = datetime.date(2001, 1, 17)
USER = "eduardo@salvador"


def uptime():
    hoje = datetime.date.today()
    anos = hoje.year - NASCIMENTO.year - ((hoje.month, hoje.day) < (NASCIMENTO.month, NASCIMENTO.day))
    ultimo = NASCIMENTO.replace(year=NASCIMENTO.year + anos)
    meses = (hoje.year - ultimo.year) * 12 + hoje.month - ultimo.month - (hoje.day < ultimo.day)
    m = ultimo.month - 1 + meses
    base = ultimo.replace(year=ultimo.year + m // 12, month=m % 12 + 1)
    dias = (hoje - base).days
    return f"{anos} years, {meses} months, {dias} days"


def gh(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-readme"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def gql(query):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "User-Agent": "profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]


def privadas():
    """Contribuicoes (commits + PRs + reviews + issues) em repositorios PRIVADOS, todos os anos.
    Precisa de um token pessoal (secret PROFILE_TOKEN) com acesso aos repos privados."""
    anos = gql(f'{{user(login:"{GH_USER}"){{contributionsCollection{{contributionYears}}}}}}')["user"]["contributionsCollection"]["contributionYears"]
    total = 0
    for a in anos:
        q = f"""{{user(login:"{GH_USER}"){{contributionsCollection(from:"{a}-01-01T00:00:00Z",to:"{a}-12-31T23:59:59Z"){{
          restrictedContributionsCount
          commitContributionsByRepository(maxRepositories:100){{repository{{isPrivate}} contributions{{totalCount}}}}
          pullRequestContributionsByRepository(maxRepositories:100){{repository{{isPrivate}} contributions{{totalCount}}}}
          pullRequestReviewContributionsByRepository(maxRepositories:100){{repository{{isPrivate}} contributions{{totalCount}}}}
          issueContributionsByRepository(maxRepositories:100){{repository{{isPrivate}} contributions{{totalCount}}}}}}}}}}"""
        cc = gql(q)["user"]["contributionsCollection"]
        total += cc["restrictedContributionsCount"]
        for k in ("commit", "pullRequest", "pullRequestReview", "issue"):
            total += sum(r["contributions"]["totalCount"] for r in cc[f"{k}ContributionsByRepository"] if r["repository"]["isPrivate"])
    return total


def linhas(repos):
    """Soma linhas adicionadas/removidas pelo usuario em cada repo (API /stats/contributors)."""
    add = rem = 0
    for r in repos:
        for _ in range(5):  # a API responde 202 enquanto calcula
            try:
                data = gh(f"https://api.github.com/repos/{r}/stats/contributors")
            except Exception:
                data = None
            if isinstance(data, list):
                break
            time.sleep(3)
        for c in data or []:
            if c.get("author") and c["author"]["login"].lower() == GH_USER.lower():
                add += sum(w["a"] for w in c["weeks"])
                rem += sum(w["d"] for w in c["weeks"])
    return add, rem


def stats():
    try:
        u = gh(f"https://api.github.com/users/{GH_USER}")
        repos, page = [], 1
        while True:
            lote = gh(f"https://api.github.com/users/{GH_USER}/repos?per_page=100&page={page}")
            repos += lote
            if len(lote) < 100:
                break
            page += 1
        stars = sum(r["stargazers_count"] for r in repos)
        commits = gh(f"https://api.github.com/search/commits?q=author:{GH_USER}")["total_count"]
        q = "https://api.github.com/search/issues?per_page=100&q="
        prs = gh(f"{q}is:pr+author:{GH_USER}")["total_count"]
        merged = gh(f"{q}is:pr+is:merged+author:{GH_USER}")["total_count"]
        oss = gh(f"{q}is:pr+is:public+author:{GH_USER}+-user:{GH_USER}")
        oss_repos = {i["repository_url"].split("repos/")[1] for i in oss["items"]}
        nomes = [r["full_name"] for r in repos]
        priv = "-"
        if os.environ.get("GITHUB_TOKEN", "").startswith(("ghp_", "github_pat_", "gho_")):  # token pessoal
            try:
                priv = privadas()
                mine = gh("https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member")
                nomes = sorted({*nomes, *(r["full_name"] for r in mine)})
            except Exception as e:
                print("privadas indisponiveis:", e)
        add, rem = linhas(nomes)
        return dict(repos=u["public_repos"], stars=stars, followers=u["followers"], commits=commits,
                    prs=prs, merged=merged, oss_prs=oss["total_count"], oss_repos=len(oss_repos),
                    priv=priv, loc=add - rem, add=add, rem=rem)
    except Exception as e:  # sem internet / limite da API
        print("stats indisponiveis:", e)
        return {k: "-" for k in ("repos", "stars", "followers", "commits", "prs", "merged", "oss_prs", "oss_repos", "priv", "loc", "add", "rem")}


S = stats()

INFO = [
    ("OS", "Windows, Ubuntu"),
    ("Uptime", uptime()),
    ("Host", "Robert Bosch"),
    ("Founder", "Corvo Ltda"),
    ("Kernel", "Full Stack Software Engineer"),
    None,
    ("Languages", "Java, Kotlin, TypeScript, Python"),
    ("Backend", "Spring Boot, Spring AI, Node.js"),
    ("Frontend", "Angular, React"),
    ("Mobile", "Android, Jetpack Compose"),
    ("Data", "SQL, NoSQL, Vector DBs"),
    ("Focus.AI", "Agents, MCP, RAG"),
    None,
    ("Hobbies", "Books, Electronics, Mercedes, Dobermanns"),
    "- Contact",
    ("LinkedIn", "in/eduardo-salvador-306480218"),
    ("Portfolio", "salvadordev.com.br"),
    "- GitHub Stats",
    ("Repos", f"{S['repos']}  {{Stars: {S['stars']}}}"),
    ("Commits", f"{S['commits']}  {{Followers: {S['followers']}}}"),
    ("Pull Requests", f"{S['prs']}  {{Merged: {S['merged']}}}"),
    ("Open Source", f"{S['oss_prs']} PRs  {{Projects: {S['oss_repos']}}}"),
    ("Lines of Code", "LOC"),
]

COLS, ROWS = 100, 42         # celulas de ~3.96 x 9.5 px -> area quadrada
RAMP = " .:-=+*#%@"
FUNDO_RAMP = " ..:"         # textura mais fraca para o circulo de fundo


def ascii_art(theme):
    # assets/mask.png = recorte da pessoa (branco) feito uma vez com GrabCut
    gray = Image.open("assets/foto_ascii.png" if os.path.exists("assets/foto_ascii.png") else FOTO).convert("L")
    msk = Image.open("assets/mask.png").convert("L")
    w, h = gray.size
    box = (int(w*.20), int(h*.06), int(w*.80), int(h*.66))  # quadrado: cabeca + ombros
    gray = gray.crop(box).filter(ImageFilter.UnsharpMask(2, 120, 2))
    msk = msk.crop(box).resize((COLS, ROWS), Image.BILINEAR)
    im = gray.resize((COLS, ROWS), Image.LANCZOS)
    pix = sorted(im.getpixel((x, y)) for y in range(ROWS) for x in range(COLS) if msk.getpixel((x, y)) > 128)
    lo, hi = pix[len(pix) // 50], pix[-len(pix) // 50]  # contraste so na pessoa
    bgp = sorted(im.getpixel((x, y)) for y in range(ROWS) for x in range(COLS) if msk.getpixel((x, y)) <= 128)
    blo, bhi = bgp[len(bgp) // 50], bgp[-len(bgp) // 50]
    out, fundo = [], []
    for y in range(ROWS):
        line, fl = "", ""
        for x in range(COLS):
            dx, dy = (x + .5) / COLS - .5, (y + .5) / ROWS - .5
            dentro = dx * dx + dy * dy <= .25
            p = im.getpixel((x, y))
            if not dentro:
                line += " "; fl += " "
            elif msk.getpixel((x, y)) > 128:
                fl += " "
                p = max(0, min(255, (p - lo) * 255 // max(1, hi - lo)))
                v = p if theme == "dark" else 255 - p
                line += RAMP[min(len(RAMP) - 1, 3 + int(v / 256 * (len(RAMP) - 3)))]  # comeca em "-" para o cabelo aparecer
            else:  # fundo redondo com textura suave
                p = max(0, min(255, (p - blo) * 255 // max(1, bhi - blo)))
                v = p if theme == "dark" else 255 - p
                fl += FUNDO_RAMP[min(len(FUNDO_RAMP) - 1, 1 + int(v / 256 * (len(FUNDO_RAMP) - 1)))]
                line += " "
        out.append(line.rstrip()); fundo.append(fl.rstrip())
    return out, fundo


def fmt(n):
    return f"{n:,}" if isinstance(n, int) else str(n)


def info_lines(width=62):
    lines = [("head", USER + " " + "-" * (width - len(USER) - 1))]
    for item in INFO:
        if item is None:
            lines.append(("blank", "."))
        elif isinstance(item, str):
            lines.append(("head", item + " " + "-" * (width - len(item) - 1)))
        else:
            k, v = item
            if v == "LOC":
                v = f"{fmt(S['loc'])} ( {fmt(S['add'])}++, {fmt(S['rem'])}-- )"
                dots = "." * max(2, width - len(k) - len(v) - 4)
                lines.append(("loc", (k, dots)))
                continue
            dots = "." * max(2, width - len(k) - len(v) - 4)
            lines.append(("kv", (k, dots, v)))
    lines.append(("prompt", ">"))
    return lines


TEMAS = {
    "dark":  dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", val="#a5d6ff", dots="#616e7f", add="#3fb950", rem="#f85149", title="#ffa657", bgart="#ffa657"),
    "light": dict(bg="#f6f8fa", fg="#24292f", key="#953800", val="#0a3069", dots="#c2cfde", add="#1a7f37", rem="#cf222e", title="#953800", bgart="#c4501a"),
}


def svg(theme):
    c = TEMAS[theme]
    (art, fundo), info = ascii_art(theme), info_lines()
    lh, ah, cw = 20, 8.3, 3.47          # altura da linha, altura do ASCII, largura do caractere ASCII
    x2, W = 375, 985
    H = max(len(art) * ah, len(info) * lh) + 30
    larg = COLS * cw
    ax = max(10, (x2 - 20 - larg) / 2)   # centraliza na coluna da esquerda
    top = 22 + (H - 30 - len(art) * ah) / 2
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{W}px" height="{H:.0f}px" font-size="15px">',
         f'<style>.k{{fill:{c["key"]}}}.v{{fill:{c["val"]}}}.d{{fill:{c["dots"]}}}.a{{fill:{c["add"]}}}.r{{fill:{c["rem"]}}}.t{{fill:{c["title"]};font-weight:bold}}text,tspan{{white-space:pre}}</style>',
         f'<rect width="{W}px" height="{H:.0f}px" fill="{c["bg"]}" rx="12"/>',
         f'<text x="{ax:.0f}" y="{top:.0f}" fill="{c["bgart"]}" font-size="6.3px">']
    for i, l in enumerate(fundo):
        s.append(f'<tspan x="{ax:.0f}" y="{top + i*ah:.1f}">{html.escape(l)}</tspan>')
    s.append(f'</text><text x="{ax:.0f}" y="{top:.0f}" fill="{c["fg"]}" font-size="6.3px">')
    for i, l in enumerate(art):
        s.append(f'<tspan x="{ax:.0f}" y="{top + i*ah:.1f}">{html.escape(l)}</tspan>')
    s.append(f'</text><text x="{x2}" y="30" fill="{c["fg"]}">')
    for i, (t, d) in enumerate(info):
        y = 30 + i * lh
        if i == 0:
            u = USER
            s.append(f'<tspan x="{x2}" y="{y}" class="t">{u}</tspan><tspan> {html.escape(d[len(u)+1:])}</tspan>')
        elif t == "kv":
            k, dots, v = d
            s.append(f'<tspan x="{x2}" y="{y}">. </tspan><tspan class="k">{html.escape(k)}</tspan>:<tspan class="d"> {dots} </tspan><tspan class="v">{html.escape(v)}</tspan>')
        elif t == "loc":
            k, dots = d
            s.append(f'<tspan x="{x2}" y="{y}">. </tspan><tspan class="k">{k}</tspan>:<tspan class="d"> {dots} </tspan>'
                     f'<tspan class="v">{fmt(S["loc"])}</tspan> ( <tspan class="a">{fmt(S["add"])}++</tspan>, <tspan class="r">{fmt(S["rem"])}--</tspan> )')
        elif t == "prompt":
            s.append(f'<tspan x="{x2}" y="{y + 10}" class="t">&gt;</tspan>')
        else:
            s.append(f'<tspan x="{x2}" y="{y}">{html.escape(d)}</tspan>')
    s.append("</text></svg>")
    return chr(10).join(s)


ICONES = {  # icones simples 22x22
    "portfolio": '<rect x="2" y="3" width="18" height="14" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M6 8l3 2-3 2M11 13h5" fill="none" stroke="{c}" stroke-width="1.8"/>',
    "linkedin": '<rect x="2" y="2" width="18" height="18" rx="3" fill="{c}"/><text x="11" y="16" text-anchor="middle" font-family="Arial" font-weight="bold" font-size="11" fill="{bg}">in</text>',
    "email": '<rect x="2" y="5" width="18" height="13" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M2 6l9 7 9-7" fill="none" stroke="{c}" stroke-width="1.8"/>',
}
CORES = {"portfolio": ("#ff7b35", "#c4501a"), "linkedin": ("#79c0ff", "#0a66c2"), "email": ("#ff7b35", "#c4501a")}


def botao(theme, nome):
    c = TEMAS[theme]
    cor = CORES[nome][0 if theme == "dark" else 1]
    ic = ICONES[nome].format(c=cor, bg=c["bg"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="48" font-family="Consolas,monospace">'
            f'<rect x="1" y="1" width="318" height="46" rx="6" fill="{c["bg"]}" stroke="{c["dots"]}" stroke-opacity=".5"/>'
            f'<rect x="1" y="44" width="318" height="3" fill="{cor}"/>'
            f'<g transform="translate({160 - len(nome)*5.2 - 20},12)">{ic}</g>'
            f'<text x="{160 + 14}" y="29" text-anchor="middle" fill="{c["fg"]}" font-size="15" letter-spacing="1">{nome.upper()}</text></svg>')


for t in ("dark", "light"):
    open(f"{t}_mode.svg", "w", encoding="utf-8").write(svg("dark"))
    for n in ("portfolio", "linkedin"):
        open(f"link_{n}_{t}.svg", "w", encoding="utf-8").write(botao("dark", n))
print("ok", S)
