"""Render the neofetch-style profile card (dark_mode.svg / light_mode.svg).

Usage:  GH_TOKEN=<token> python scripts/neofetch.py
Without a token the GitHub stats section falls back to the REST API (no commit totals).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import random
import urllib.request
from html import escape
from pathlib import Path

USER = "Reriiii"
ROOT = Path(__file__).resolve().parent.parent

# ───────────────────────────── content ─────────────────────────────
# 7-row pixel font for the logo word
GLYPHS = {
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "I": ["111", "010", "010", "010", "010", "010", "111"],
}
LOGO_WORD = "RERI"


def info_lines(stats: dict[str, str]) -> list:
    """Each entry: ("title", text) | ("section", text) | ("kv", key, value) | ("blank",)."""
    return [
        ("title", "quoc@reriiii"),
        ("rule",),
        ("kv", "Name", "Trần Kiến Quốc"),
        ("kv", "Role", "AI Engineer · Applied ML Research"),
        ("kv", "Focus", "Vision-Language Models, Document AI, Agents"),
        ("kv", "Motto", "Rise from Regret, Reach for Tomorrow"),
        ("blank",),
        ("section", "Research"),
        ("kv", "PGVA (CLIP + LoRA)", "150K params · 35.23 OOD macro-F1"),
        ("kv", "Mini-CoMER (HMER)", "6.39M params · 47.9% ExpRate"),
        ("kv", "TexTeller4Chemical", "in progress"),
        ("kv", "Research Desk", "observable LangGraph agent"),
        ("blank",),
        ("section", "Stack"),
        ("kv", "Languages", "Python, C++, TypeScript"),
        ("kv", "Modeling", "PyTorch, Transformers, PEFT, CLIP"),
        ("kv", "Agents", "LangGraph, OpenAI, Gemini, Ollama"),
        ("kv", "Serving", "FastAPI, React, HF Spaces, Vercel"),
        ("blank",),
        ("section", "Contact"),
        ("kv", "Email", "quockientran100@gmail.com"),
        ("kv", "LinkedIn", "in/reri"),
        ("kv", "Hugging Face", "quoctk31"),
        ("blank",),
        ("section", "GitHub Stats"),
        ("kv2", "Repos", stats["repos"], "Stars", stats["stars"]),
        ("kv2", "Contributions", stats["contribs"], "Followers", stats["followers"]),
    ]


# ───────────────────────────── stats ─────────────────────────────
def _req(url: str, token: str | None, body: dict | None = None) -> dict:
    headers = {"User-Agent": "reriiii-neofetch", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"bearer {token}"
    data = json.dumps(body).encode() if body else None
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=30) as r:
        return json.load(r)


def _gql(token: str, query: str, **variables) -> dict:
    out = _req("https://api.github.com/graphql", token, {"query": query, "variables": variables})
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def fetch_stats() -> dict[str, str]:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        repos = _req(f"https://api.github.com/users/{USER}/repos?per_page=100", None)
        own = [r for r in repos if not r["fork"]]
        user = _req(f"https://api.github.com/users/{USER}", None)
        return {
            "repos": str(len(own)),
            "stars": str(sum(r["stargazers_count"] for r in own)),
            "followers": str(user["followers"]),
            "contribs": "n/a",
        }

    base = _gql(
        token,
        """query($login:String!){user(login:$login){createdAt followers{totalCount}
        repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
        totalCount nodes{stargazerCount}}}}""",
        login=USER,
    )["user"]
    start_year = int(base["createdAt"][:4])
    now = dt.datetime.now(dt.timezone.utc)
    contribs = 0
    for year in range(start_year, now.year + 1):
        frm = f"{year}-01-01T00:00:00Z"
        to = now.strftime("%Y-%m-%dT%H:%M:%SZ") if year == now.year else f"{year}-12-31T23:59:59Z"
        contribs += _gql(
            token,
            """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
            contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions}}}}""",
            login=USER, **{"from": frm, "to": to},
        )["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return {
        "repos": str(base["repositories"]["totalCount"]),
        "stars": str(sum(n["stargazerCount"] for n in base["repositories"]["nodes"])),
        "followers": str(base["followers"]["totalCount"]),
        "contribs": f"{contribs:,}",
    }


# ───────────────────────────── attention heatmap ─────────────────────────────
def attention(n: int = 12, seed: int = 7) -> list[list[float]]:
    """Synthetic causal self-attention: strong diagonal, an attention sink on token 0, some noise."""
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        logits = []
        for j in range(i + 1):
            s = rnd.gauss(0, 0.6)
            s += 2.4 if j == i else 0
            s += 1.4 if j == i - 1 else 0
            s += 2.0 if j == 0 else 0
            logits.append(s)
        m = max(logits)
        exps = [math.exp(x - m) for x in logits]
        z = sum(exps)
        rows.append([e / z for e in exps] + [0.0] * (n - i - 1))
    return rows


# ───────────────────────────── svg ─────────────────────────────
THEMES = {
    "dark": dict(bg="#0d1117", bar="#161b22", border="#30363d", text="#c9d1d9", key="#ffa657",
                 value="#a5d6ff", dots="#484f58", accent="#45c7e8", title="#58a6ff", muted="#8b949e",
                 cell="#45c7e8", empty="#161b22"),
    "light": dict(bg="#f6f8fa", bar="#eaeef2", border="#d0d7de", text="#24292f", key="#953800",
                  value="#0a3069", dots="#afb8c1", accent="#0969da", title="#0969da", muted="#57606a",
                  cell="#0969da", empty="#eaeef2"),
}

FONT = 16
LH = 21           # line height
CW = 9.6          # approx. monospace char width at 16px (used only for layout boxes)
RIGHT_COLS = 56   # width of key/value lines in chars
PAD_X, BAR_H = 28, 34
LEFT_X = PAD_X
RIGHT_X = 360


def kv(key: str, value: str, width: int = RIGHT_COLS) -> tuple[str, str, str]:
    dots = max(2, width - len(key) - len(value) - 4)
    return key, " " + "." * dots + " ", value


def render(theme: str, stats: dict[str, str]) -> str:
    c = THEMES[theme]
    lines = info_lines(stats)
    top = BAR_H + 36
    height = top + LH * len(lines) + 28
    width = RIGHT_X + int(RIGHT_COLS * CW) + PAD_X + 6

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="ConsolasFallback,Consolas,\'JetBrains Mono\',Menlo,monospace" '
        f'font-size="{FONT}px">',
        "<style>",
        "@font-face{font-family:ConsolasFallback;src:local('Consolas');size-adjust:109%}",
        f".k{{fill:{c['key']}}}.v{{fill:{c['value']}}}.d{{fill:{c['dots']}}}.t{{fill:{c['text']}}}"
        f".a{{fill:{c['accent']}}}.m{{fill:{c['muted']}}}.h{{fill:{c['title']};font-weight:bold}}",
        "text,tspan{white-space:pre}",
        ".cur{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}",
        "</style>",
        f'<rect width="{width}" height="{height}" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>',
        f'<path d="M12 0.5h{width - 24}a11.5 11.5 0 0 1 11.5 11.5v{BAR_H - 12}h-{width - 1}v-{BAR_H - 12}a11.5 11.5 0 0 1 11.5-11.5z" fill="{c["bar"]}"/>',
        f'<line x1="0.5" y1="{BAR_H}" x2="{width - 0.5}" y2="{BAR_H}" stroke="{c["border"]}"/>',
    ]
    for i, col in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        out.append(f'<circle cx="{22 + i * 20}" cy="{BAR_H / 2}" r="6" fill="{col}"/>')
    out.append(f'<text x="{width / 2}" y="{BAR_H / 2 + 5}" text-anchor="middle" class="m" font-size="13px">'
               f'quoc@reriiii: ~ — neofetch</text>')

    # left: pixel logo with a drop shadow
    hx = LEFT_X + 6
    px, pgap = 13, 2
    y = top - 14
    col = 0
    shadow, front = [], []
    for ch in LOGO_WORD:
        glyph = GLYPHS[ch]
        for r, row in enumerate(glyph):
            for k, bit in enumerate(row):
                if bit == "1":
                    x0, y0 = hx + (col + k) * px, y + r * px
                    shadow.append(f'<rect x="{x0 + 3}" y="{y0 + 3}" width="{px - pgap}" height="{px - pgap}" rx="2" '
                                  f'fill="{c["accent"]}" fill-opacity="0.22"/>')
                    front.append(f'<rect x="{x0}" y="{y0}" width="{px - pgap}" height="{px - pgap}" rx="2" '
                                 f'fill="{c["accent"]}"/>')
        col += len(glyph[0]) + 1
    out += shadow + front

    # left: attention heatmap
    att = attention()
    n = len(att)
    cell, gap = 20, 3
    hy = y + 7 * px + 40
    out.append(f'<text x="{hx}" y="{hy}" class="m" font-size="13px">causal self-attention · head 0</text>')
    hy += 12
    peak = max(max(r) for r in att)
    for i in range(n):
        for j in range(n):
            x0, y0 = hx + j * (cell + gap), hy + i * (cell + gap)
            if j > i:
                out.append(f'<rect x="{x0}" y="{y0}" width="{cell}" height="{cell}" rx="3" '
                           f'fill="{c["empty"]}"/>')
            else:
                op = 0.12 + 0.88 * (att[i][j] / peak) ** 0.7
                out.append(f'<rect x="{x0}" y="{y0}" width="{cell}" height="{cell}" rx="3" '
                           f'fill="{c["cell"]}" fill-opacity="{op:.2f}"/>')
    out.append(f'<text x="{hx}" y="{hy + n * (cell + gap) + 16}" class="m" font-size="12px">'
               f'tokens → (rows attend to past only)</text>')

    # right: info
    out.append(f'<text x="{RIGHT_X}" y="{top}">')
    for idx, ln in enumerate(lines):
        yy = top + idx * LH
        kind = ln[0]
        t = f'<tspan x="{RIGHT_X}" y="{yy}"'
        if kind == "title":
            out.append(f'{t} class="h">{escape(ln[1])}</tspan>')
        elif kind == "rule":
            out.append(f'{t} class="d">{"─" * RIGHT_COLS}</tspan>')
        elif kind == "section":
            label = f"─ {ln[1]} "
            out.append(f'{t} class="h">{escape(label)}<tspan class="d">{"─" * (RIGHT_COLS - len(label))}</tspan></tspan>')
        elif kind == "kv":
            k, d, v = kv(ln[1], ln[2])
            out.append(f'{t} class="k">{escape(k)}:</tspan><tspan class="d">{d}</tspan><tspan class="v">{escape(v)}</tspan>')
        elif kind == "kv2":
            half = RIGHT_COLS // 2 - 1
            k1, d1, v1 = kv(ln[1], ln[2], half)
            k2, d2, v2 = kv(ln[3], ln[4], RIGHT_COLS - half - 3)
            out.append(f'{t} class="k">{escape(k1)}:</tspan><tspan class="d">{d1}</tspan><tspan class="v">{escape(v1)}</tspan>'
                       f'<tspan class="d"> | </tspan><tspan class="k">{escape(k2)}:</tspan><tspan class="d">{d2}</tspan>'
                       f'<tspan class="v">{escape(v2)}</tspan>')
    out.append("</text>")
    # blinking cursor under the last line
    out.append(f'<text x="{RIGHT_X}" y="{top + len(lines) * LH}" class="a"><tspan>$ </tspan>'
               f'<tspan class="cur">█</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    stats = fetch_stats()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, stats), encoding="utf-8")
    print("stats:", stats)


if __name__ == "__main__":
    main()
