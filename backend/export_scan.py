"""Export a scan as a standalone HTML page.

Runs every mode through the scanner and writes one self-contained page --
no server, no browser, no network beyond the usual Yahoo Finance fetch that
the scanner already does (and caches under backend/.cache/).

    python export_scan.py                     # all three modes, top 20 each
    python export_scan.py --limit 50          # deeper lists
    python export_scan.py --tickers AAPL,MSFT # ad-hoc list instead of the universe
    python export_scan.py --out reports/today.html
    python export_scan.py --allow-overlap     # let a name appear in several lists

Each stock is listed under exactly one mode by default. Where a name qualifies
for several, precedence is Confirmed Breakout, then Early Breakout, then Strong
Bullish Trend.

The page is designed to be published or shared as-is: it inlines its own CSS,
renders in light and dark, and carries the full 13-point checklist per row.
"""
import argparse
import datetime
import html
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scanner import service  # noqa: E402
from app.scanner.modes import (  # noqa: E402
    ALL_MODES,
    EARLY_BREAKOUT,
    CONFIRMED_BREAKOUT,
    STRONG_BULLISH_TREND,
)

# Prose for the page. The one-liners in modes.MODE_DESCRIPTIONS are written for
# the app's tab strip; these spell out what each gate actually requires.
MODE_TITLES = {
    EARLY_BREAKOUT: "Early Breakout",
    CONFIRMED_BREAKOUT: "Confirmed Breakout",
    STRONG_BULLISH_TREND: "Strong Bullish Trend",
}

MODE_BLURBS = {
    EARLY_BREAKOUT:
        "Price has just reclaimed the 20 SMA while still inside a tight (&lt;20%) consolidation, "
        "near its 20-day high. The widest net: more candidates, higher risk of a failed move.",
    CONFIRMED_BREAKOUT:
        "A breakout of more than 0.5% off the prior 20-day high, within 5% of the 20/50-day high, "
        "relative volume at least 0.8&times;, price above the 20 SMA. The main screen &mdash; "
        "fewest names, highest bar.",
    STRONG_BULLISH_TREND:
        "A full 20&gt;50&gt;200 SMA stack with price above the 200 SMA, RSI 50&ndash;80, ADX at "
        "least 15. Trend quality only &mdash; these names need not be breaking out today.",
}

# The 12 boolean conditions behind the 13-point score, in scoring order.
# rs_vs_spy is worth 2 points; every other condition is worth 1.
CONDITIONS = [
    ("price_gt_sma20",     "P&gt;20",   "Price above the 20-day SMA", 1),
    ("price_gt_sma50",     "P&gt;50",   "Price above the 50-day SMA", 1),
    ("price_gt_sma200",    "P&gt;200",  "Price above the 200-day SMA", 1),
    ("sma20_gt_sma50",     "20&gt;50",  "20 SMA above 50 SMA", 1),
    ("sma50_gt_sma200",    "50&gt;200", "50 SMA above 200 SMA", 1),
    ("rsi_in_range",       "RSI",       "RSI(14) between 55 and 75", 1),
    ("adx_strong",         "ADX",       "ADX(14) above 20", 1),
    ("di_bullish",         "DI",        "+DI above -DI", 1),
    ("rvol_strong",        "VOL",       "Relative volume above 1.0x", 1),
    ("breakout_confirmed", "B/O",       "Breakout greater than 0.5%", 1),
    ("near_high",          "HIGH",      "Within 5% of the 20/50-day high", 1),
    ("rs_vs_spy",          "RS",        "3-month return beats SPY (worth 2 points)", 2),
]

# When a stock qualifies for more than one mode it is listed once, under the
# first mode here: the strictest, most time-sensitive signal wins, and the
# background trend screen picks up whatever is left.
MODE_PRECEDENCE = [CONFIRMED_BREAKOUT, EARLY_BREAKOUT, STRONG_BULLISH_TREND]

RATING_CLASS = {
    "Strong Bullish": "strong",
    "Bullish": "bull",
    "Watchlist": "watch",
    "Ignore": "ignore",
}

# Relative volume or breakout beyond these is almost always a corporate action
# or a bad vendor bar rather than real price action. The scanner still scores
# such a row, so the page marks it instead of letting it rank silently.
RVOL_SUSPECT = 10.0
BREAKOUT_SUSPECT = 25.0

# Effectively "no cap" when pulling a mode's candidate pool before de-duplication.
FETCH_ALL = 1_000_000


def signed(v, dp=2):
    return ("+" if v >= 0 else "−") + "{:.{dp}f}".format(abs(v), dp=dp)


def is_suspect(r):
    return (r["relative_volume"] or 0) > RVOL_SUSPECT or abs(r["breakout_pct"] or 0) > BREAKOUT_SUSPECT


def cond_strip(score):
    cells = []
    for key, label, title, weight in CONDITIONS:
        on = "on" if score.get(key) else "off"
        wide = " wide" if weight == 2 else ""
        cells.append('<span class="cond {on}{wide}" title="{t}">{l}</span>'.format(
            on=on, wide=wide, t=title, l=label))
    return '<span class="strip">' + "".join(cells) + "</span>"


def meter(total, max_total):
    return '<span class="meter" aria-hidden="true">{}</span>'.format(
        "".join('<i class="{}"></i>'.format("f" if i < total else "e")
                for i in range(max_total)))


def render_row(i, r):
    s = r["score"]
    rs = r["rs_vs_spy_pct"] or 0.0
    r3 = r["return_3m_pct"] or 0.0
    flag = is_suspect(r)
    return """<tr{trc}>
<td class="rank">{i}</td>
<td class="sym"><span class="tkr">{sym}{badge}</span><span class="nm">{name}</span><span class="sec">{sector}</span></td>
<td class="num">${price}</td>
<td class="score">{meter}<span class="sv">{total}<span class="sd">/{maxt}</span></span></td>
<td><span class="pill {rc}">{rating}</span></td>
<td class="checks">{strip}</td>
<td class="num">{rsi}</td>
<td class="num">{adx}</td>
<td class="num{rvc}">{rvol}&times;</td>
<td class="num{boc}">{bo}%</td>
<td class="num {r3c}">{r3}%</td>
<td class="num {rsc}">{rs}%</td>
</tr>""".format(
        trc=' class="flagged"' if flag else "",
        i=i,
        sym=html.escape(r["symbol"]),
        badge=('<span class="warn" title="Relative volume or breakout far outside normal range '
               '&mdash; likely a corporate action or bad data bar, not a tradeable breakout.">check data</span>'
               if flag else ""),
        name=html.escape(r["name"] or ""),
        sector=html.escape(r.get("sector") or ""),
        price="{:,.2f}".format(r["price"]),
        meter=meter(s["total"], s["max_total"]),
        total=s["total"], maxt=s["max_total"],
        rc=RATING_CLASS.get(r["rating"], "ignore"),
        rating=html.escape(r["rating"]),
        strip=cond_strip(s),
        rsi="{:.1f}".format(r["rsi14"] or 0),
        adx="{:.1f}".format(r["adx14"] or 0),
        rvol="{:.2f}".format(r["relative_volume"] or 0),
        rvc=" odd" if (r["relative_volume"] or 0) > RVOL_SUSPECT else "",
        bo=signed(r["breakout_pct"] or 0),
        boc=" odd" if abs(r["breakout_pct"] or 0) > BREAKOUT_SUSPECT else " pos",
        r3=signed(r3), r3c="pos" if r3 >= 0 else "neg",
        rs=signed(rs), rsc="pos" if rs >= 0 else "neg",
    )


def render_section(mode, payload, limit):
    res = payload["results"]
    if not res:
        body = '<p class="empty">No names cleared this mode’s gates on this scan.</p>'
    else:
        body = """<div class="scroll"><table>
<thead><tr>
<th class="rank">#</th><th>Symbol</th><th class="num">Price</th><th>Score</th><th>Rating</th>
<th>Conditions met</th><th class="num">RSI</th><th class="num">ADX</th><th class="num">RVol</th>
<th class="num">Breakout</th><th class="num">3M</th><th class="num">vs SPY</th>
</tr></thead>
<tbody>{rows}</tbody></table></div>""".format(
            rows="\n".join(render_row(i + 1, r) for i, r in enumerate(res)))

    strong = sum(1 for r in res if r["rating"] == "Strong Bullish")
    flagged = sum(1 for r in res if is_suspect(r))
    bits = ["<b>{}</b> {}".format(len(res), "match" if len(res) == 1 else "matches")]
    if len(res) == limit:
        bits.append("capped at top {}".format(limit))
    bits.append("<b>{}</b> rated Strong Bullish".format(strong))
    if flagged:
        bits.append('<b class="flagn">{}</b> flagged for suspect data'.format(flagged))

    return """<section class="mode" id="{mode}">
<div class="mhead">
<h2>{title}</h2>
<p class="gate">{blurb}</p>
<p class="mcount">{bits}</p>
</div>
{body}
</section>""".format(mode=mode, title=MODE_TITLES[mode], blurb=MODE_BLURBS[mode],
                     bits=" &middot; ".join(bits), body=body)


DEDUPED_NOTE = ("Every name appears in exactly one list. A stock that qualifies for several "
                "modes is assigned by precedence &mdash; Confirmed Breakout, then Early Breakout, "
                "then Strong Bullish Trend &mdash; so the strictest signal wins and no ticker repeats.")
OVERLAP_NOTE = "Modes overlap &mdash; a name can appear in more than one list."


def render_page(payloads, limit, source_note, overlap_note):
    ref = payloads[CONFIRMED_BREAKOUT]
    spy = ref.get("spy_return_3m_pct")
    if spy is None:
        for p in payloads.values():
            if p.get("spy_return_3m_pct") is not None:
                spy = p["spy_return_3m_pct"]
                break
    spy = spy or 0.0

    legend = "".join('<li><span class="cond on{w}">{l}</span> {t}</li>'.format(
        w=" wide" if weight == 2 else "", l=label, t=title)
        for key, label, title, weight in CONDITIONS)

    sections = "\n".join(render_section(m, payloads[m], limit) for m in ALL_MODES)

    # Staleness is per-fetch, not per-mode: the union across modes is what matters.
    stale = sorted({s for p in payloads.values() for s in p.get("stale_symbols", [])})
    failed = max([p.get("failed_count", 0) for p in payloads.values()] or [0])
    if stale or failed:
        parts = []
        if stale:
            parts.append(
                "<b>{}</b> symbol(s) are showing cached prices older than the 4-hour "
                "refresh window, because the upstream fetch failed for them. Those rows "
                "are not current.".format(len(stale)))
        if failed:
            parts.append(
                "<b>{}</b> symbol(s) returned no usable data and were skipped.".format(failed))
        syms = ""
        if stale:
            shown = " ".join(stale[:40])
            if len(stale) > 40:
                shown += " +{} more".format(len(stale) - 40)
            syms = '<span class="syms">{}</span>'.format(shown)
        stale_banner = '<div class="stale">{}{}</div>'.format(" ".join(parts), syms)
    else:
        stale_banner = ""


    return """<title>Bullish Breakout Scan</title>
<style>
:root {{
  --bg:#EEF1F4; --surface:#FFFFFF; --surface2:#F6F8FA; --raise:#FBFCFD;
  --ink:#131C24; --ink2:#4A5A68; --ink3:#84939F;
  --line:#D6DEE5; --line2:#E7ECF1;
  --accent:#A85D2B; --accent-soft:#F1E3D7;
  --gain:#17705A; --loss:#A83A33; --odd:#8A5A9B; --odd-bg:#F0E6F4;
  --strong-bg:#E2EFE9; --strong-fg:#14624E;
  --bull-bg:#E6EFE3; --bull-fg:#3F6B32;
  --watch-bg:#F5EDD9; --watch-fg:#7A6017;
  --ignore-bg:#EAEEF1; --ignore-fg:#5C6B77;
  --shadow:0 1px 2px rgba(19,28,36,.05), 0 8px 24px -12px rgba(19,28,36,.18);
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#0E141A; --surface:#151D25; --surface2:#1A232C; --raise:#1E2831;
    --ink:#E6EDF3; --ink2:#9FB2C0; --ink3:#6D8190;
    --line:#26333D; --line2:#1F2A33;
    --accent:#D9873F; --accent-soft:#33251A;
    --gain:#4FBB97; --loss:#E2776D; --odd:#C79BD8; --odd-bg:#2C1F33;
    --strong-bg:#14312A; --strong-fg:#63C9A6;
    --bull-bg:#1B2E19; --bull-fg:#89C079;
    --watch-bg:#31290F; --watch-fg:#D6B25A;
    --ignore-bg:#202931; --ignore-fg:#8497A4;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
  }}
}}
:root[data-theme="dark"] {{
  --bg:#0E141A; --surface:#151D25; --surface2:#1A232C; --raise:#1E2831;
  --ink:#E6EDF3; --ink2:#9FB2C0; --ink3:#6D8190;
  --line:#26333D; --line2:#1F2A33;
  --accent:#D9873F; --accent-soft:#33251A;
  --gain:#4FBB97; --loss:#E2776D; --odd:#C79BD8; --odd-bg:#2C1F33;
  --strong-bg:#14312A; --strong-fg:#63C9A6;
  --bull-bg:#1B2E19; --bull-fg:#89C079;
  --watch-bg:#31290F; --watch-fg:#D6B25A;
  --ignore-bg:#202931; --ignore-fg:#8497A4;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 28px -14px rgba(0,0,0,.7);
}}

* {{ box-sizing:border-box; }}
body {{
  background:var(--bg); color:var(--ink);
  font-family:"Segoe UI", system-ui, -apple-system, sans-serif;
  font-size:15px; line-height:1.55; margin:0;
  padding:clamp(20px,4vw,56px) clamp(14px,4vw,40px) 72px;
  -webkit-font-smoothing:antialiased;
}}
.wrap {{ max-width:1180px; margin:0 auto; display:flex; flex-direction:column; gap:44px; }}

header {{ display:flex; flex-direction:column; gap:18px; }}
.eyebrow {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0;
}}
h1 {{
  font-family:ui-serif,"Iowan Old Style",Georgia,serif;
  font-size:clamp(30px,5vw,46px); line-height:1.08; font-weight:600;
  letter-spacing:-.015em; margin:0; text-wrap:balance;
}}
.sub {{ color:var(--ink2); margin:0; max-width:62ch; }}

.funnel {{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(132px,1fr)); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:10px;
  overflow:hidden; box-shadow:var(--shadow); margin-top:6px;
}}
.fcell {{ background:var(--surface); padding:14px 16px; display:flex; flex-direction:column; gap:3px; }}
.fcell .k {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:10px; letter-spacing:.13em; text-transform:uppercase; color:var(--ink3);
}}
.fcell .v {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:23px; font-variant-numeric:tabular-nums; letter-spacing:-.02em; color:var(--ink);
}}
.fcell .v.pos {{ color:var(--gain); }}
.fcell .v.neg {{ color:var(--loss); }}

.legend {{
  background:var(--surface); border:1px solid var(--line); border-radius:10px;
  padding:18px 20px; box-shadow:var(--shadow);
}}
.legend h3 {{
  font-size:11px; letter-spacing:.13em; text-transform:uppercase; color:var(--ink3);
  margin:0 0 12px; font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; font-weight:600;
}}
.legend ul {{
  list-style:none; margin:0; padding:0;
  display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:8px 22px;
}}
.legend li {{ display:flex; align-items:center; gap:9px; font-size:13px; color:var(--ink2); }}

.mode {{ display:flex; flex-direction:column; gap:14px; }}
.mhead {{ display:flex; flex-direction:column; gap:6px; border-left:3px solid var(--accent); padding-left:15px; }}
.mode h2 {{
  font-family:ui-serif,"Iowan Old Style",Georgia,serif;
  font-size:clamp(20px,2.6vw,26px); font-weight:600; letter-spacing:-.01em; margin:0;
}}
.gate {{ margin:0; color:var(--ink2); max-width:74ch; font-size:14px; }}
.mcount {{
  margin:2px 0 0; font-size:12px; color:var(--ink3);
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
}}
.mcount b {{ color:var(--ink); font-weight:600; }}
.mcount b.flagn {{ color:var(--odd); }}
.empty {{
  margin:0; padding:22px; text-align:center; color:var(--ink3);
  background:var(--surface); border:1px dashed var(--line); border-radius:10px;
}}

.scroll {{
  overflow-x:auto; background:var(--surface);
  border:1px solid var(--line); border-radius:10px; box-shadow:var(--shadow);
}}
table {{ border-collapse:collapse; width:100%; min-width:1040px; }}
thead th {{
  position:sticky; top:0; background:var(--surface2); z-index:1;
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:10px; letter-spacing:.11em; text-transform:uppercase; color:var(--ink3);
  font-weight:600; text-align:left; padding:11px 12px; border-bottom:1px solid var(--line);
  white-space:nowrap;
}}
thead th.num, td.num {{ text-align:right; }}
tbody td {{ padding:11px 12px; border-bottom:1px solid var(--line2); vertical-align:middle; }}
tbody tr:last-child td {{ border-bottom:none; }}
tbody tr:hover td {{ background:var(--raise); }}
tbody tr.flagged td {{ background:var(--odd-bg); }}
td.num {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px; white-space:nowrap; color:var(--ink);
}}
td.num.pos {{ color:var(--gain); }}
td.num.neg {{ color:var(--loss); }}
td.num.odd {{ color:var(--odd); font-weight:700; }}
td.rank, th.rank {{
  width:34px; text-align:right; color:var(--ink3);
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; font-size:12px;
}}
td.sym {{ display:flex; flex-direction:column; gap:1px; min-width:172px; }}
.tkr {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-weight:700; font-size:14px; letter-spacing:.02em;
}}
.warn {{
  display:inline-block; margin-left:7px; padding:1px 6px; border-radius:3px;
  background:var(--odd-bg); color:var(--odd); border:1px solid var(--odd);
  font-size:8.5px; letter-spacing:.08em; text-transform:uppercase; font-weight:700;
  vertical-align:middle; cursor:default;
}}
.nm {{ font-size:12.5px; color:var(--ink2); }}
.sec {{
  font-size:10px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink3);
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
}}

td.score {{ white-space:nowrap; }}
.meter {{ display:inline-flex; gap:1.5px; vertical-align:middle; margin-right:9px; }}
.meter i {{ width:4px; height:17px; border-radius:1px; display:block; }}
.meter i.f {{ background:var(--accent); }}
.meter i.e {{ background:var(--line); }}
.sv {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:13px; font-weight:700; font-variant-numeric:tabular-nums; vertical-align:middle;
}}
.sd {{ font-weight:400; color:var(--ink3); }}

.pill {{
  display:inline-block; padding:3px 9px; border-radius:999px; white-space:nowrap;
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:10.5px; letter-spacing:.06em; text-transform:uppercase; font-weight:600;
}}
.pill.strong {{ background:var(--strong-bg); color:var(--strong-fg); }}
.pill.bull   {{ background:var(--bull-bg);   color:var(--bull-fg); }}
.pill.watch  {{ background:var(--watch-bg);  color:var(--watch-fg); }}
.pill.ignore {{ background:var(--ignore-bg); color:var(--ignore-fg); }}

.strip {{ display:inline-flex; gap:2px; }}
.cond {{
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:9px; letter-spacing:.02em; line-height:1;
  padding:4px 4px; border-radius:2px; min-width:26px; text-align:center;
  border:1px solid transparent; cursor:default; white-space:nowrap;
}}
.cond.wide {{ min-width:32px; font-weight:700; }}
.cond.on {{ background:var(--accent-soft); color:var(--accent); border-color:var(--accent-soft); }}
.cond.off {{ background:transparent; color:var(--ink3); border-color:var(--line); opacity:.6; }}

.stale {{
  background:var(--odd-bg); border:1px solid var(--odd); border-radius:10px;
  padding:14px 18px; color:var(--odd); font-size:13.5px; line-height:1.5;
}}
.stale b {{ font-weight:700; }}
.stale .syms {{
  display:block; margin-top:6px; font-size:11.5px; opacity:.85;
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace; word-break:break-word;
}}

footer {{
  border-top:1px solid var(--line); padding-top:20px;
  color:var(--ink3); font-size:12.5px; display:flex; flex-direction:column; gap:7px;
}}
footer b {{ color:var(--ink2); font-weight:600; }}
@media (max-width:640px) {{ .legend ul {{ grid-template-columns:1fr 1fr; }} }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">Scan run {stamp}</p>
  <h1>Bullish Breakout Scan</h1>
  <p class="sub">Every name that cleared each mode&rsquo;s gates on this run, ranked by the 13-point
  bullish score rather than pass/fail filters. {source_note} Prices and indicators via Yahoo Finance.</p>
  <div class="funnel">
    <div class="fcell"><span class="k">Universe</span><span class="v">{universe}</span></div>
    <div class="fcell"><span class="k">Eligible</span><span class="v">{eligible}</span></div>
    <div class="fcell"><span class="k">Scanned</span><span class="v">{scanned}</span></div>
    <div class="fcell"><span class="k">Early b/o</span><span class="v">{n_early}</span></div>
    <div class="fcell"><span class="k">Confirmed</span><span class="v">{n_conf}</span></div>
    <div class="fcell"><span class="k">Trend</span><span class="v">{n_trend}</span></div>
    <div class="fcell"><span class="k">SPY 3M</span><span class="v {spyc}">{spy}%</span></div>
  </div>
</header>

{stale_banner}
<div class="legend">
  <h3>The 13-point score</h3>
  <ul>{legend}</ul>
</div>

{sections}

<footer>
  <span>Universe eligibility applied before any mode: market cap above <b>$1B</b>, three-month average volume above <b>500K</b>. Each mode hard-gates only on the conditions that define its character; everything else feeds the score.</span>
  <span>{overlap_note} Each list is capped at the top <b>{limit}</b> by score.</span>
  <span>Rows marked <b>check data</b> have relative volume above {rvol_lim}&times; or a breakout above {bo_lim}% &mdash; almost always a corporate action or a bad vendor bar rather than a tradeable move. The scanner scores them anyway; treat them as data errors until verified.</span>
  <span>Static snapshot of one scan. Research and educational use only &mdash; not investment advice.</span>
</footer>
</div>
""".format(
        stamp=datetime.datetime.now().strftime("%d %b %Y &middot; %H:%M local"),
        stale_banner=stale_banner,
        source_note=source_note,
        universe=ref["universe_size"],
        eligible=ref["eligible_count"],
        scanned=ref["scanned_count"],
        n_early=len(payloads[EARLY_BREAKOUT]["results"]),
        n_conf=len(payloads[CONFIRMED_BREAKOUT]["results"]),
        n_trend=len(payloads[STRONG_BULLISH_TREND]["results"]),
        spy=signed(spy), spyc="pos" if spy >= 0 else "neg",
        limit=limit, overlap_note=overlap_note,
        rvol_lim=int(RVOL_SUSPECT), bo_lim=int(BREAKOUT_SUSPECT),
        legend=legend, sections=sections,
    )


def main(argv=None):
    default_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports", "scan.html")
    ap = argparse.ArgumentParser(description="Export a scan as a standalone HTML page.")
    ap.add_argument("--limit", type=int, default=20, help="rows per mode (default 20)")
    ap.add_argument("--out", default=default_out, help="output path (default backend/exports/scan.html)")
    ap.add_argument("--tickers", default=None,
                    help="comma separated tickers to scan instead of the default universe")
    ap.add_argument("--allow-overlap", action="store_true",
                    help="let a stock appear in several mode lists (default: each name listed once)")
    args = ap.parse_args(argv)

    source_note = ("Scanned an ad-hoc ticker list rather than the default universe."
                   if args.tickers else "")

    # Pull each mode's full ranked candidate pool, not just the top N. Trimming
    # happens after de-duplication so a name claimed by a stricter mode does not
    # leave a hole in the list it was dropped from.
    payloads = {}
    for mode in ALL_MODES:
        print("scanning {} ...".format(mode), flush=True)
        resp = service.run_scan(mode=mode, limit=FETCH_ALL, custom_tickers=args.tickers)
        payloads[mode] = resp.model_dump()

    if args.allow_overlap:
        for mode in ALL_MODES:
            payloads[mode]["results"] = payloads[mode]["results"][:args.limit]
    else:
        claimed = set()
        for mode in MODE_PRECEDENCE:
            kept = []
            for r in payloads[mode]["results"]:
                if r["symbol"] in claimed:
                    continue
                kept.append(r)
                claimed.add(r["symbol"])
                if len(kept) >= args.limit:
                    break
            payloads[mode]["results"] = kept

    page = render_page(payloads, args.limit, source_note,
                       OVERLAP_NOTE if args.allow_overlap else DEDUPED_NOTE)

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write(page)

    ref = payloads[CONFIRMED_BREAKOUT]
    print()
    print("universe {}  eligible {}  scanned {}".format(
        ref["universe_size"], ref["eligible_count"], ref["scanned_count"]))
    for mode in ALL_MODES:
        res = payloads[mode]["results"]
        flagged = sum(1 for r in res if is_suspect(r))
        print("  {:<22} {:>2} matches{}".format(
            mode, len(res), "  ({} flagged)".format(flagged) if flagged else ""))
    print()
    print("wrote {} ({:,} bytes)".format(out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
