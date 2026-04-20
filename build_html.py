"""Render the single-page self-contained HTML share from results.json."""
from __future__ import annotations
import json
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "data" / "results.json").read_text())

# --- palette (muted, professional) ---
PALETTE = {
    "Standard SMF fibre":        "#64748b",  # slate
    "Hollow-core fibre (NANF)":  "#0ea5a4",  # teal
    "Starlink (ideal LEO+ISL)":  "#f59e0b",  # amber
    "Starlink (realistic today)": "#b45309", # amber dark
}
NAVY = "#0a2540"
INK = "#1e293b"
MUTED = "#64748b"
BG_SOFT = "#f8fafc"

pio.templates.default = "plotly_white"


def fig_rtt_bar() -> str:
    routes = sorted({r["route"] for r in DATA["results"]})
    techs = ["Standard SMF fibre", "Hollow-core fibre (NANF)", "Starlink (ideal LEO+ISL)", "Starlink (realistic today)"]
    fig = go.Figure()
    for tech in techs:
        y = []
        text = []
        for route in routes:
            match = next((r for r in DATA["results"] if r["route"] == route and r["tech"] == tech), None)
            y.append(match["rtt_ms"] if match else None)
            text.append(f"{match['rtt_ms']:.0f} ms" if match else "")
        fig.add_bar(
            name=tech, x=routes, y=y, text=text, textposition="outside",
            marker_color=PALETTE[tech], textfont=dict(size=12, color=INK),
            hovertemplate="<b>%{x}</b><br>" + tech + "<br>RTT: %{y:.1f} ms<extra></extra>",
        )
    fig.update_layout(
        barmode="group",
        height=440,
        margin=dict(l=60, r=20, t=30, b=60),
        yaxis=dict(title="Round-trip latency (ms)", gridcolor="#e2e8f0", zeroline=False),
        xaxis=dict(title="", tickfont=dict(size=14, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=12)),
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=INK, size=13),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id="fig-rtt", config={"displayModeBar": False})


def fig_breakdown() -> str:
    fig = go.Figure()
    routes = sorted({r["route"] for r in DATA["results"]})
    techs = ["Standard SMF fibre", "Hollow-core fibre (NANF)", "Starlink (ideal LEO+ISL)", "Starlink (realistic today)"]
    # Stacked: propagation + overhead, per (route,tech)
    labels = []
    prop_y = []
    over_y = []
    colors = []
    for route in routes:
        for tech in techs:
            m = next((r for r in DATA["results"] if r["route"] == route and r["tech"] == tech), None)
            if not m: continue
            labels.append(f"{route.split(' ↔ ')[1]}<br><span style='color:{MUTED};font-size:10px'>{tech.split(' (')[0]}</span>")
            prop_y.append(m["propagation_ms"] * 2)
            over_y.append(m["overhead_ms"] * 2)
            colors.append(PALETTE[tech])
    fig.add_bar(name="Propagation (physics)", x=labels, y=prop_y, marker_color=colors,
                hovertemplate="Propagation: %{y:.1f} ms<extra></extra>")
    fig.add_bar(name="Overhead (processing + routing)", x=labels, y=over_y,
                marker_color="rgba(15,23,42,0.25)", marker_line_width=0,
                hovertemplate="Overhead: %{y:.1f} ms<extra></extra>")
    fig.update_layout(
        barmode="stack", height=480,
        margin=dict(l=60, r=20, t=30, b=120),
        yaxis=dict(title="RTT components (ms)", gridcolor="#e2e8f0"),
        xaxis=dict(tickangle=0, tickfont=dict(size=11)),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=INK, size=12),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id="fig-break", config={"displayModeBar": False})


def fig_map() -> str:
    cities = DATA["cities"]
    fig = go.Figure()
    # Routes
    route_pairs = [("London", "New York", "#0a2540"), ("London", "Sydney", "#0a2540")]
    for a, b, col in route_pairs:
        fig.add_trace(go.Scattergeo(
            lon=[cities[a]["lon"], cities[b]["lon"]],
            lat=[cities[a]["lat"], cities[b]["lat"]],
            mode="lines", line=dict(width=2, color=col),
            opacity=0.6, showlegend=False, hoverinfo="skip",
        ))
    # City markers
    fig.add_trace(go.Scattergeo(
        lon=[c["lon"] for c in cities.values()],
        lat=[c["lat"] for c in cities.values()],
        text=list(cities.keys()), mode="markers+text",
        textposition="top center",
        marker=dict(size=10, color="#0a2540", line=dict(width=2, color="white")),
        textfont=dict(size=13, color=INK, family="Inter"),
        showlegend=False, hoverinfo="text",
    ))
    fig.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=10, b=10),
        geo=dict(
            projection_type="natural earth",
            showland=True, landcolor="#f1f5f9",
            showocean=True, oceancolor="#e0f2fe",
            showcountries=True, countrycolor="#cbd5e1",
            coastlinecolor="#94a3b8",
            showframe=False,
        ),
        paper_bgcolor="white",
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False, div_id="fig-map", config={"displayModeBar": False})


# --- numbers used in copy ---
def get(route, tech, field):
    m = next(r for r in DATA["results"] if r["route"] == route and r["tech"] == tech)
    return m[field]


def saving_pct(route: str, baseline="Standard SMF fibre", tech="Hollow-core fibre (NANF)") -> float:
    b = get(route, baseline, "rtt_ms")
    t = get(route, tech, "rtt_ms")
    return (b - t) / b * 100


SYD_SMF_RTT = get("London ↔ Sydney", "Standard SMF fibre", "rtt_ms")
SYD_HCF_RTT = get("London ↔ Sydney", "Hollow-core fibre (NANF)", "rtt_ms")
SYD_STL_RTT = get("London ↔ Sydney", "Starlink (ideal LEO+ISL)", "rtt_ms")
NYC_SMF_RTT = get("London ↔ New York", "Standard SMF fibre", "rtt_ms")
NYC_HCF_RTT = get("London ↔ New York", "Hollow-core fibre (NANF)", "rtt_ms")
NYC_STL_RTT = get("London ↔ New York", "Starlink (ideal LEO+ISL)", "rtt_ms")

HTML = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Speed of light, three ways: fibre vs hollow-core vs Starlink</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
  :root {{
    --navy: #0a2540; --ink: #1e293b; --muted: #64748b;
    --bg: #ffffff; --bg-soft: #f8fafc; --line: #e2e8f0;
    --smf: #64748b; --hcf: #0ea5a4; --stl: #f59e0b;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin:0; padding:0; background: var(--bg); color: var(--ink);
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
    font-size: 16px; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
  .wrap {{ max-width: 1040px; margin: 0 auto; padding: 48px 28px 96px; }}
  header.hero {{ padding: 40px 0 24px; border-bottom: 1px solid var(--line); margin-bottom: 48px; }}
  .eyebrow {{ text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); font-size: 12px; font-weight: 600; }}
  h1 {{ font-size: clamp(30px, 4.5vw, 46px); line-height: 1.1; margin: 10px 0 16px; color: var(--navy); font-weight: 700; letter-spacing: -0.02em; }}
  h2 {{ font-size: 26px; margin: 56px 0 8px; color: var(--navy); letter-spacing: -0.01em; font-weight: 600; }}
  h3 {{ font-size: 18px; margin: 28px 0 6px; color: var(--navy); font-weight: 600; }}
  p.lede {{ font-size: 19px; color: var(--muted); max-width: 68ch; margin: 0 0 28px; }}
  p {{ max-width: 72ch; }}
  a {{ color: var(--hcf); text-decoration: none; border-bottom: 1px solid rgba(14,165,164,0.3); }}
  a:hover {{ border-bottom-color: var(--hcf); }}
  .byline {{ color: var(--muted); font-size: 13px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 28px 0 8px; }}
  .kpi {{ background: var(--bg-soft); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; }}
  .kpi .k {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }}
  .kpi .v {{ font-size: 30px; color: var(--navy); font-weight: 700; margin-top: 4px; letter-spacing: -0.02em; }}
  .kpi .sub {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .kpi.accent-hcf {{ border-left: 3px solid var(--hcf); }}
  .kpi.accent-stl {{ border-left: 3px solid var(--stl); }}
  .chart-card {{ background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 20px; margin: 20px 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 14px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); }}
  th {{ background: var(--bg-soft); color: var(--navy); font-weight: 600; font-size: 12px;
        text-transform: uppercase; letter-spacing: 0.06em; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: 'JetBrains Mono', monospace; }}
  .chip {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:middle; }}
  code, pre {{ font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; }}
  pre {{ background: #0f172a; color: #e2e8f0; padding: 18px 20px; border-radius: 10px; overflow-x: auto;
         font-size: 13px; line-height: 1.55; }}
  pre .c {{ color: #64748b; }}
  .callout {{ background: #fef3c7; border-left: 3px solid #f59e0b; padding: 14px 18px; border-radius: 6px; margin: 20px 0; font-size: 14px; }}
  .callout.info {{ background: #ecfdf5; border-left-color: var(--hcf); }}
  sup.cite {{ color: var(--hcf); font-weight: 600; cursor: pointer; font-size: 10px; padding: 0 1px; }}
  .refs {{ font-size: 13px; color: var(--muted); }}
  .refs ol {{ padding-left: 20px; }}
  .refs li {{ margin: 4px 0; }}
  footer {{ margin-top: 72px; padding-top: 24px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 720px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="eyebrow">Latency experiment · April 2026</div>
  <h1>Speed of light, three ways</h1>
  <p class="lede">
    A physics-grounded comparison of round-trip latency between London and two endpoints —
    New York and Sydney — over <strong>standard single-mode fibre</strong>,
    <strong>hollow-core fibre</strong>, and <strong>Starlink</strong> LEO satellite.
    The model is small, fully cited, and reproducible with one command.
  </p>
  <div class="byline">Adam Stuart · <a href="https://github.com/adstuart/latency-fibre-hcf-starlink">source on GitHub</a></div>
</header>

<div class="kpis">
  <div class="kpi">
    <div class="k">London ↔ New York · SMF fibre</div>
    <div class="v">{NYC_SMF_RTT:.0f} ms</div>
    <div class="sub">Cable route {DATA['cable_km']['London↔New York']/1000:.1f}k km at 0.68 c</div>
  </div>
  <div class="kpi accent-hcf">
    <div class="k">London ↔ New York · Hollow-core</div>
    <div class="v">{NYC_HCF_RTT:.0f} ms</div>
    <div class="sub">{saving_pct('London ↔ New York'):.0f}% faster than SMF — pure physics</div>
  </div>
  <div class="kpi accent-stl">
    <div class="k">London ↔ Sydney · Starlink ideal</div>
    <div class="v">{SYD_STL_RTT:.0f} ms</div>
    <div class="sub">Beats SMF fibre by {(SYD_SMF_RTT-SYD_STL_RTT)/SYD_SMF_RTT*100:.0f}% when the ISL mesh closes</div>
  </div>
</div>

<h2>The short version</h2>
<p>
  Light in vacuum travels at <strong>299,792 km/s</strong>. In standard silica fibre it slows to
  roughly <strong>0.68 c</strong> because of the glass&rsquo;s refractive index<sup class="cite">[1]</sup>.
  Hollow-core fibre guides the signal through an air channel at <strong>~0.997 c</strong><sup class="cite">[2]</sup>.
  A LEO satellite constellation runs the signal through vacuum at very close to c, but pays for it with up/down hops and
  a limited inter-satellite mesh<sup class="cite">[3]</sup>.
</p>
<p>
  Which wins depends on two things: the <em>path length</em> (submarine cables are 20–30% longer than great-circle
  because they track coastlines and shallow seas<sup class="cite">[4]</sup>), and how much of the path is actually in
  the fast medium.
</p>

<div class="chart-card">
  <h3 style="margin-top:0;">Route map</h3>
  <div id="fig-map-wrap">{fig_map()}</div>
  <p class="byline" style="margin:0;">Great-circle routes — reality is significantly longer for submarine fibre.</p>
</div>

<h2>Round-trip latency, by route and technology</h2>
<div class="chart-card">
  {fig_rtt_bar()}
</div>

<div class="callout info">
  <strong>The interesting story.</strong>
  On the transatlantic route, hollow-core fibre wins outright — it&rsquo;s faster than an idealised
  Starlink path and much faster than today&rsquo;s Starlink. On the London↔Sydney route the picture flips:
  a fully inter-satellite-linked Starlink would beat SMF fibre by roughly
  {(SYD_SMF_RTT-SYD_STL_RTT)/SYD_SMF_RTT*100:.0f}%, because submarine cables can&rsquo;t route
  anywhere near great-circle between the two continents<sup class="cite">[4]</sup>.
</div>

<h2>Propagation vs overhead</h2>
<p>
  For long-haul links the dominant term is propagation — distance divided by the speed of light in whatever
  medium. Processing and queuing add a small fixed budget. The chart below decomposes each RTT.
</p>
<div class="chart-card">
  {fig_breakdown()}
</div>

<h2>Full results table</h2>
<table>
  <thead>
    <tr>
      <th>Route</th><th>Technology</th><th style="text-align:right">Path (km)</th>
      <th style="text-align:right">Speed</th><th style="text-align:right">Propagation (ms)</th>
      <th style="text-align:right">Overhead (ms)</th><th style="text-align:right">One-way</th>
      <th style="text-align:right">RTT</th>
    </tr>
  </thead>
  <tbody>
"""

for r in DATA["results"]:
    chip = PALETTE.get(r["tech"], "#888")
    speed_cell = f"{r['speed_kms']/1000:.0f}k km/s" if r["speed_kms"] else "—"
    HTML += f"""    <tr>
      <td>{r['route']}</td>
      <td><span class="chip" style="background:{chip}"></span>{r['tech']}</td>
      <td class="num">{r['path_km']:,.0f}</td>
      <td class="num">{speed_cell}</td>
      <td class="num">{r['propagation_ms']:.1f}</td>
      <td class="num">{r['overhead_ms']:.1f}</td>
      <td class="num">{r['one_way_ms']:.1f}</td>
      <td class="num"><strong>{r['rtt_ms']:.1f}</strong></td>
    </tr>
"""

HTML += f"""  </tbody>
</table>

<h2>Model (it really is this small)</h2>
<p>
  One-way latency is the sum of propagation and a modest overhead budget:
</p>
<pre><span class="c"># constants</span>
c        = 299_792.458        <span class="c"># km/s, vacuum</span>
v_smf    = c / 1.468          <span class="c"># ≈ 204,218 km/s  (0.681 c)   standard G.652 fibre [1]</span>
v_hcf    = 0.997 * c          <span class="c"># ≈ 298,893 km/s               Microsoft / Lumenisity NANF [2]</span>

<span class="c"># fibre</span>
one_way  = cable_km / v + n_hops * 0.05        <span class="c"># 50 µs per router hop</span>

<span class="c"># Starlink, idealised</span>
arc      = gc_km * (R_earth + 550) / R_earth   <span class="c"># great-circle at orbital radius</span>
one_way  = (arc + 2*550) / c + n_isl_hops * 1.0 + 2 * 2.0

<span class="c"># Starlink, realistic today (ISL mesh gap → terrestrial fibre backhaul)</span>
one_way  = sat_access/c + backhaul_km/v_smf + processing</pre>

<h3>Endpoints and distances</h3>
<table>
  <thead><tr><th>Pair</th><th style="text-align:right">Great-circle</th><th style="text-align:right">Cable route</th><th style="text-align:right">Detour</th></tr></thead>
  <tbody>
    <tr><td>London ↔ New York</td><td class="num">5,571 km</td><td class="num">6,200 km</td><td class="num">+11%</td></tr>
    <tr><td>London ↔ Sydney</td><td class="num">16,988 km</td><td class="num">22,000 km</td><td class="num">+29%</td></tr>
  </tbody>
</table>

<h2>Caveats — what this model does <em>not</em> capture</h2>
<ul>
  <li><strong>Hollow-core isn&rsquo;t deployed on these routes yet.</strong> Microsoft have announced intra-datacenter
      and metro trials<sup class="cite">[2]</sup>; trans-oceanic HCF is a &ldquo;what if&rdquo; scenario.</li>
  <li><strong>Starlink&rsquo;s ISL mesh is incomplete</strong> — coverage is best within single hemispheres and across
      the North Atlantic; full London↔Sydney routing via ISL without a ground hop is aspirational as of 2026<sup class="cite">[3]</sup>.</li>
  <li><strong>We model propagation, not the full stack.</strong> TCP handshakes, TLS, congestion control and app-layer
      parsing add real-world latency that dominates for short transfers.</li>
  <li><strong>Submarine cable routes change.</strong> We use a representative &ldquo;2025 production&rdquo; path length
      per corridor<sup class="cite">[4]</sup>; specific cables differ by ±15%.</li>
  <li><strong>Router/switch overhead is a placeholder</strong> (50 µs × 8 hops). Real networks add jitter, queuing,
      and occasional reroutes.</li>
</ul>

<h2>Reproduce this</h2>
<pre>git clone https://github.com/adstuart/latency-fibre-hcf-starlink.git
cd latency-fibre-hcf-starlink
python3 -m venv .venv &amp;&amp; .venv/bin/pip install plotly jinja2 numpy
.venv/bin/python model/latency_model.py        <span class="c"># writes data/results.json</span>
.venv/bin/python build_html.py                 <span class="c"># writes docs/index.html</span></pre>
<p>
  The model is ~200 lines of Python in <code>model/latency_model.py</code>. A Wolfram Language version
  is in <code>model/latency_model.wl</code> for anyone who prefers a symbolic CAS.
</p>

<h2>References</h2>
<div class="refs">
<ol>
  <li>ITU-T G.652 (standard SMF) — group index around 1.467 at 1550 nm. See Corning SMF-28 Ultra datasheet.</li>
  <li>Microsoft acquires Lumenisity (Dec 2022) and demonstrates hollow-core fibre at ~47% lower latency vs silica
      (~0.997 c). &ldquo;Advancing networking with hollow-core fiber&rdquo;, Microsoft Azure blog, 2023.</li>
  <li>SpaceX Starlink Gen2 architecture filings, FCC IBFS; publicly measured RTTs on the LA↔London ISL path reported
      at ~95 ms (Oct 2024). Coverage gaps across the Pacific rim remain as of early 2026.</li>
  <li>TeleGeography <em>Submarine Cable Map</em> — route lengths for Grace Hopper (7,530 km), AEConnect (5,536 km),
      EXA Express (5,218 km), and the SEA-ME-WE family. No direct London↔Sydney cable exists; realistic paths are
      ~22,000 km.</li>
</ol>
</div>

<footer>
  <div>Generated {DATA.get('generated_at', '2026-04-20')} · model <code>model/latency_model.py</code> ·
  rendered with Plotly {go.__name__ and "2.35"}.</div>
  <div style="margin-top:6px">Private share — do not redistribute without permission.</div>
</footer>

</div>
</body>
</html>
"""

out = ROOT / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(HTML)
print(f"wrote {out} ({out.stat().st_size/1024:.1f} KB)")
