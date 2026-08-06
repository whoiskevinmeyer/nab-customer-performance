#!/usr/bin/env python3
"""Build NAB customer performance dashboard — month-filterable, compare modes."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

FILES = {
    "Standard": Path(
        "/Users/kevinmeyer/.hermes/cache/documents/doc_8c8e828e2348_20260806_Standard_Products.xlsx"
    ),
    "Non_Standard": Path(
        "/Users/kevinmeyer/.hermes/cache/documents/doc_a22b8ecd8c9e_20260806_Non_Standard_Products.xlsx"
    ),
    "OEM": Path(
        "/Users/kevinmeyer/.hermes/cache/documents/doc_a328db5ab3bf_20260806_OEM_Products.xlsx"
    ),
}

OUTS = [
    Path("/Users/kevinmeyer/projects/matilda-dashboard/public/pm-wholesale-movers.html"),
    Path("/Users/kevinmeyer/projects/matilda-dashboard/dist/pm-wholesale-movers.html"),
    Path("/Users/kevinmeyer/.hermes/cache/documents/pm-wholesale-movers.html"),
    Path("/tmp/pm-movers-www/index.html"),
    Path("/Users/kevinmeyer/projects/nab-customer-performance/public/index.html"),
]

SEG_LABEL = {"D_R": "Resellers", "End_User": "End Users", "OEM_KA": "OEM"}
MONTH_NUM = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def load_all() -> pd.DataFrame:
    frames = []
    for label, path in FILES.items():
        df = pd.read_excel(path, header=2)
        df.columns = [str(c).strip() for c in df.columns]
        df["ProductClass"] = label
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["Customer"] = df["Customer"].astype(str).str.strip()
    df["Business Type"] = df["Business Type"].astype(str).str.strip()
    df["Sales Amount"] = pd.to_numeric(df["Sales Amount"], errors="coerce").fillna(0.0)
    df["YQM - Year"] = pd.to_numeric(df["YQM - Year"], errors="coerce").astype(int)
    df["YearMonth"] = df["YQM - YearMonthName"].astype(str).str.strip()

    def parse_ym(s: str):
        parts = str(s).split()
        if len(parts) == 2 and parts[1] in MONTH_NUM:
            y = int(parts[0])
            m = MONTH_NUM[parts[1]]
            return y, m, y * 100 + m
        return None, None, None

    parsed = df["YearMonth"].map(parse_ym)
    df["year"] = [p[0] for p in parsed]
    df["month"] = [p[1] for p in parsed]
    df["ymKey"] = [p[2] for p in parsed]
    df = df.dropna(subset=["ymKey"])
    df["ymKey"] = df["ymKey"].astype(int)
    return df


def build_payload(df: pd.DataFrame) -> dict:
    # Distinct months sorted
    months_df = (
        df[["YearMonth", "year", "month", "ymKey"]]
        .drop_duplicates()
        .sort_values("ymKey")
    )
    months = [
        {
            "label": r.YearMonth,
            "year": int(r.year),
            "month": int(r.month),
            "key": int(r.ymKey),
        }
        for r in months_df.itertuples()
    ]

    # Customer x segment x month grain
    g = (
        df.groupby(
            ["Customer", "Business Type", "YearMonth", "year", "month", "ymKey"],
            dropna=False,
        )["Sales Amount"]
        .sum()
        .reset_index()
    )
    facts = []
    for _, r in g.iterrows():
        facts.append(
            {
                "c": str(r["Customer"]),
                "s": str(r["Business Type"]),
                "ym": str(r["YearMonth"]),
                "y": int(r["year"]),
                "m": int(r["month"]),
                "k": int(r["ymKey"]),
                "v": round(float(r["Sales Amount"]), 2),
            }
        )

    # Segment-month totals for charts
    sm = (
        df.groupby(["Business Type", "YearMonth", "year", "month", "ymKey"])["Sales Amount"]
        .sum()
        .reset_index()
        .sort_values("ymKey")
    )
    segment_month = [
        {
            "s": str(r["Business Type"]),
            "ym": str(r["YearMonth"]),
            "y": int(r["year"]),
            "m": int(r["month"]),
            "k": int(r["ymKey"]),
            "v": round(float(r["Sales Amount"]), 2),
        }
        for _, r in sm.iterrows()
    ]

    return {
        "meta": {
            "title": "NAB Customer Performance",
            "subtitle": "Wholesale movers · Resellers · End Users · OEM",
            "asOf": "2026-08-06",
            "sources": [
                "20260806_Standard_Products.xlsx",
                "20260806_Non_Standard_Products.xlsx",
                "20260806_OEM_Products.xlsx",
            ],
            "notes": [
                "Default period is latest-year YTD so Previous year compare is meaningful. Expand From to include earlier months if needed.",
        "Month range filter limits both current and comparison windows.",
                "Compare shifts the selected window back by 1 month, 1 quarter (3 months), or 1 year (12 months).",
                "Rankings use absolute $ delta (current window vs compare window).",
                "Business Type from Power BI: D_R = Resellers, End_User, OEM_KA = OEM.",
                "Organic mode hides accounts with $0 in the compare window (new ramps).",
            ],
            "rowCount": int(len(df)),
            "factCount": len(facts),
        },
        "segLabels": SEG_LABEL,
        "months": months,
        "facts": facts,
        "segmentMonth": segment_month,
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>NAB Customer Performance</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0b0f14;
    --panel: #121821;
    --panel2: #182131;
    --border: #243041;
    --text: #e8eef7;
    --muted: #8b9bb0;
    --green: #3dd68c;
    --red: #ff6b7a;
    --blue: #5b9dff;
    --amber: #f5c542;
    --purple: #b388ff;
    --radius: 14px;
    --font: "Segoe UI", system-ui, -apple-system, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; font-family: var(--font);
    background: radial-gradient(1200px 600px at 10% -10%, #152238 0%, var(--bg) 55%);
    color: var(--text); min-height: 100vh;
  }}
  header {{
    padding: 20px 28px 10px; display: flex; flex-wrap: wrap; gap: 16px;
    justify-content: space-between; align-items: flex-end;
  }}
  h1 {{ margin: 0; font-size: 1.5rem; letter-spacing: -0.02em; }}
  .sub {{ color: var(--muted); font-size: .9rem; margin-top: 6px; max-width: 760px; line-height: 1.4; }}
  .badge {{
    display: inline-flex; gap: 8px; background: var(--panel); border: 1px solid var(--border);
    border-radius: 999px; padding: 8px 14px; color: var(--muted); font-size: .8rem;
  }}
  .badge strong {{ color: var(--text); }}
  main {{ padding: 10px 28px 40px; display: grid; gap: 14px; }}
  .filters {{
    display: grid; grid-template-columns: 1.4fr 1fr; gap: 12px;
  }}
  @media (max-width: 960px) {{ .filters {{ grid-template-columns: 1fr; }} header, main, footer {{ padding-left: 14px; padding-right: 14px; }} }}
  .card {{
    background: linear-gradient(180deg, var(--panel) 0%, #0f141c 100%);
    border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px;
  }}
  .card h3 {{
    margin: 0 0 8px; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
    color: var(--muted); font-weight: 600;
  }}
  .card .val {{ font-size: 1.35rem; font-weight: 700; letter-spacing: -0.02em; }}
  .card .delta {{ margin-top: 5px; font-size: .82rem; font-weight: 600; }}
  .up {{ color: var(--green); }} .down {{ color: var(--red); }} .muted {{ color: var(--muted); }} .new {{ color: var(--amber); }}
  .kpis {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }}
  @media (max-width: 1100px) {{ .kpis {{ grid-template-columns: repeat(3, 1fr); }} }}
  @media (max-width: 700px) {{ .kpis {{ grid-template-columns: repeat(2, 1fr); }} }}
  .filter-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: end; }}
  label {{ display: grid; gap: 4px; font-size: .72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; font-weight: 600; }}
  select, button.tab {{
    border: 1px solid var(--border); background: var(--panel2); color: var(--text);
    border-radius: 10px; padding: 9px 12px; font-size: .88rem; font-weight: 600;
  }}
  select {{ min-width: 132px; }}
  .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .tab {{ cursor: pointer; border-radius: 999px; color: var(--muted); }}
  .tab.active {{ background: #1e3a5f; color: #d7e8ff; border-color: #2f5f98; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  @media (max-width: 1000px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}
  table {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
  th, td {{ padding: 9px 7px; border-bottom: 1px solid var(--border); text-align: right; white-space: nowrap; }}
  th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
  th {{ color: var(--muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .05em; }}
  tr {{ cursor: pointer; }}
  tr:hover td {{ background: rgba(255,255,255,.025); }}
  tr.selected td {{ background: rgba(91,157,255,.08); }}
  .name {{ font-weight: 600; }}
  .pill {{
    display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: .7rem; font-weight: 700;
    background: var(--panel2); border: 1px solid var(--border); color: var(--muted);
  }}
  .pill.res {{ color: #9fd0ff; }} .pill.eu {{ color: #b8f0d0; }} .pill.oem {{ color: #e2c6ff; }}
  .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  @media (max-width: 900px) {{ .charts {{ grid-template-columns: 1fr; }} }}
  .chart-wrap {{ position: relative; height: 270px; }}
  .chart-wrap.tall {{ height: 300px; }}
  .notes {{ color: var(--muted); font-size: .8rem; line-height: 1.45; }}
  .detail {{ display: none; }} .detail.show {{ display: block; }}
  .detail h2 {{ margin: 0 0 6px; font-size: 1.1rem; }}
  .range-label {{ color: var(--text); font-size: .85rem; font-weight: 600; margin-top: 8px; }}
  footer {{ color: var(--muted); font-size: .75rem; padding: 0 28px 24px; }}
</style>
</head>
<body>
<header>
  <div>
    <h1 id="title">NAB Customer Performance</h1>
    <div class="sub" id="subtitle"></div>
  </div>
  <div class="badge">As of <strong id="asof"></strong> · <span id="rowcount"></span> source lines</div>
</header>
<main>
  <section class="filters">
    <div class="card">
      <h3>Period</h3>
      <div class="filter-row">
        <label>From month
          <select id="fromMonth"></select>
        </label>
        <label>To month
          <select id="toMonth"></select>
        </label>
        <label>Compare to
          <select id="compareMode">
            <option value="prev_year" selected>Previous year</option>
            <option value="prev_quarter">Previous quarter</option>
            <option value="prev_month">Previous month</option>
          </select>
        </label>
      </div>
      <div class="range-label" id="rangeLabel"></div>
    </div>
    <div class="card">
      <h3>Segment · ranking mode</h3>
      <div class="filter-row">
        <div class="tabs" id="segTabs"></div>
        <div class="tabs" id="modeTabs">
          <button class="tab active" data-mode="delta" type="button">By $ delta</button>
          <button class="tab" data-mode="organic" type="button">Organic (had compare $)</button>
        </div>
      </div>
    </div>
  </section>

  <section class="kpis" id="kpis"></section>

  <section class="charts">
    <div class="card">
      <h3>Segment sales · current vs compare</h3>
      <div class="chart-wrap"><canvas id="segChart"></canvas></div>
    </div>
    <div class="card">
      <h3>Monthly sales by segment (full history)</h3>
      <div class="chart-wrap"><canvas id="monthChart"></canvas></div>
    </div>
  </section>

  <section class="grid-2">
    <div class="card">
      <h3 style="color:var(--green);text-transform:none;letter-spacing:0;font-size:.9rem">▲ Top 20 accelerating</h3>
      <div style="overflow:auto"><table id="accTable"><thead></thead><tbody></tbody></table></div>
    </div>
    <div class="card">
      <h3 style="color:var(--red);text-transform:none;letter-spacing:0;font-size:.9rem">▼ Top 20 declining</h3>
      <div style="overflow:auto"><table id="decTable"><thead></thead><tbody></tbody></table></div>
    </div>
  </section>

  <section class="card detail" id="detail">
    <h2 id="detailTitle">Company</h2>
    <div class="sub" id="detailMeta"></div>
    <div class="chart-wrap tall" style="margin-top:12px"><canvas id="detailChart"></canvas></div>
  </section>

  <section class="card">
    <h3>New / ramp in current window (compare = $0, current ≥ $10k)</h3>
    <div style="overflow:auto"><table id="newTable"><thead></thead><tbody></tbody></table></div>
  </section>

  <section class="card notes">
    <h3>Notes</h3>
    <ul id="notes"></ul>
  </section>
</main>
<footer>NAB Customer Performance · no login · data embedded from Power BI extracts</footer>

<script id="payload" type="application/json">{data_json}</script>
<script>
const DATA = JSON.parse(document.getElementById('payload').textContent);
const SEG_PILL = {{ D_R: 'res', End_User: 'eu', OEM_KA: 'oem' }};
const SEG_ORDER = ['D_R','End_User','OEM_KA'];
let seg = 'ALL';
let mode = 'delta';
let selectedKey = null;
let segChart, monthChart, detailChart;

const months = DATA.months; // sorted
const monthIndex = Object.fromEntries(months.map((m,i)=>[m.key,i]));

const fmt = (n) => {{
  const v = Number(n)||0;
  const sign = v < 0 ? '-' : '';
  const a = Math.abs(v);
  if (a >= 1e6) return sign + '$' + (a/1e6).toFixed(2) + 'M';
  if (a >= 1e3) return sign + '$' + (a/1e3).toFixed(1) + 'K';
  return sign + '$' + a.toLocaleString(undefined, {{maximumFractionDigits: 0}});
}};
const pct = (n) => n == null ? 'New' : ((n>0?'+':'') + n.toFixed(1) + '%');
const deltaCls = (n) => n > 0 ? 'up' : (n < 0 ? 'down' : 'muted');

function shiftKey(key, deltaMonths) {{
  let y = Math.floor(key/100);
  let m = key % 100;
  let idx = y*12 + (m-1) + deltaMonths;
  const ny = Math.floor(idx/12);
  const nm = (idx % 12) + 1;
  return ny*100 + nm;
}}

function selectedRangeKeys() {{
  const from = Number(document.getElementById('fromMonth').value);
  const to = Number(document.getElementById('toMonth').value);
  const a = Math.min(from,to), b = Math.max(from,to);
  return months.filter(m => m.key >= a && m.key <= b).map(m => m.key);
}}

function compareRangeKeys(currKeys) {{
  if (!currKeys.length) return [];
  const mode = document.getElementById('compareMode').value;
  const delta = mode === 'prev_month' ? -1 : mode === 'prev_quarter' ? -3 : -12;
  return currKeys.map(k => shiftKey(k, delta));
}}

function labelForKeys(keys) {{
  if (!keys.length) return '—';
  const labs = keys.map(k => {{
    const m = months.find(x => x.key === k);
    return m ? m.label : String(k);
  }});
  if (labs.length === 1) return labs[0];
  return labs[0] + ' → ' + labs[labs.length-1] + ' (' + labs.length + ' mo)';
}}

function sumFacts(pred) {{
  let t = 0;
  for (const f of DATA.facts) if (pred(f)) t += f.v;
  return t;
}}

function compute() {{
  const currKeys = new Set(selectedRangeKeys());
  const cmpKeysArr = compareRangeKeys([...currKeys]);
  const cmpKeys = new Set(cmpKeysArr);
  const segFilter = seg === 'ALL' ? null : seg;

  // Aggregate per customer+segment
  const map = new Map();
  for (const f of DATA.facts) {{
    if (segFilter && f.s !== segFilter) continue;
    const inC = currKeys.has(f.k);
    const inP = cmpKeys.has(f.k);
    if (!inC && !inP) continue;
    const key = f.c + '\\t' + f.s;
    let row = map.get(key);
    if (!row) {{
      row = {{ customer: f.c, segment: f.s, segmentLabel: DATA.segLabels[f.s]||f.s, current: 0, compare: 0, monthly: [] }};
      map.set(key, row);
    }}
    if (inC) row.current += f.v;
    if (inP) row.compare += f.v;
  }}
  // monthly full history for selected companies later — keep all facts by company for detail
  const rows = [...map.values()].map(r => {{
    const delta = r.current - r.compare;
    let p = null;
    let status = 'flat';
    if (r.compare > 0) p = (delta / r.compare) * 100;
    else if (r.current > 0) {{ p = null; status = 'new'; }}
    if (r.current <= 0 && r.compare > 0) status = 'churned';
    else if (delta > 0 && status !== 'new') status = 'up';
    else if (delta < 0) status = 'down';
    return {{
      ...r,
      current: round2(r.current),
      compare: round2(r.compare),
      delta: round2(delta),
      pct: p == null ? null : round1(p),
      status
    }};
  }});

  // segment totals
  const segTotals = SEG_ORDER.map(s => {{
    let current = 0, compare = 0;
    for (const f of DATA.facts) {{
      if (f.s !== s) continue;
      if (currKeys.has(f.k)) current += f.v;
      if (cmpKeys.has(f.k)) compare += f.v;
    }}
    return {{
      segment: s,
      label: DATA.segLabels[s]||s,
      current: round2(current),
      compare: round2(compare),
      delta: round2(current-compare)
    }};
  }});

  let totalC = 0, totalP = 0;
  for (const s of segTotals) {{ totalC += s.current; totalP += s.compare; }}

  let acc = rows.filter(r => r.delta > 0 && (r.compare >= 1000 || r.current >= 5000));
  acc.sort((a,b) => b.delta - a.delta);
  let organic = acc.filter(r => r.compare > 0);
  let dec = rows.filter(r => r.delta < 0 && r.compare >= 1000);
  dec.sort((a,b) => a.delta - b.delta);
  let news = rows.filter(r => r.compare <= 0 && r.current >= 10000);
  news.sort((a,b) => b.current - a.current);

  if (mode === 'organic') acc = organic;

  return {{
    currKeys: [...currKeys].sort((a,b)=>a-b),
    cmpKeys: cmpKeysArr.slice().sort((a,b)=>a-b),
    totalC: round2(totalC),
    totalP: round2(totalP),
    delta: round2(totalC-totalP),
    segTotals,
    acc: acc.slice(0,20),
    dec: dec.slice(0,20),
    news: news.slice(0,20),
  }};
}}

function round2(n){{ return Math.round(n*100)/100; }}
function round1(n){{ return Math.round(n*10)/10; }}

function initControls() {{
  const from = document.getElementById('fromMonth');
  const to = document.getElementById('toMonth');
  const opts = months.map(m => `<option value="${{m.key}}">${{m.label}}</option>`).join('');
  from.innerHTML = opts;
  to.innerHTML = opts;
  // Default: latest year YTD (or last 12 months) so prev-year compare yields real declines.
  // Full-span + prev_year makes current include prior year and almost never declines.
  const latestYear = months[months.length - 1].year;
  const ytdStart = months.find(m => m.year === latestYear) || months[Math.max(0, months.length - 12)];
  from.value = ytdStart.key;
  to.value = months[months.length - 1].key;
  from.onchange = onFilter;
  to.onchange = onFilter;
  document.getElementById('compareMode').onchange = onFilter;

  const tabs = [
    ['ALL','All'],
    ['D_R','Resellers'],
    ['End_User','End Users'],
    ['OEM_KA','OEM'],
  ];
  const el = document.getElementById('segTabs');
  el.innerHTML = tabs.map(([id,label]) =>
    `<button class="tab ${{id===seg?'active':''}}" data-seg="${{id}}" type="button">${{label}}</button>`
  ).join('');
  el.querySelectorAll('button').forEach(b => b.onclick = () => {{
    seg = b.dataset.seg; selectedKey=null; renderAll();
  }});
  document.querySelectorAll('#modeTabs .tab').forEach(b => {{
    b.onclick = () => {{ mode = b.dataset.mode; selectedKey=null; renderAll(); }};
  }});
}}

function onFilter() {{
  // keep from <= to visually
  const from = document.getElementById('fromMonth');
  const to = document.getElementById('toMonth');
  if (Number(from.value) > Number(to.value)) {{
    // allow either order; compute uses min/max
  }}
  selectedKey = null;
  renderAll();
}}

function renderHeader() {{
  document.getElementById('title').textContent = DATA.meta.title;
  document.getElementById('subtitle').textContent = DATA.meta.subtitle;
  document.getElementById('asof').textContent = DATA.meta.asOf;
  document.getElementById('rowcount').textContent = DATA.meta.rowCount.toLocaleString();
  document.getElementById('notes').innerHTML = DATA.meta.notes.map(n => `<li>${{n}}</li>`).join('');
}}

function renderKpis(st) {{
  const cards = [
    {{ h: 'Current period', v: fmt(st.totalC), d: labelForKeys(st.currKeys), cls: 'muted' }},
    {{ h: 'Compare period', v: fmt(st.totalP), d: labelForKeys(st.cmpKeys), cls: 'muted' }},
    {{ h: 'Delta', v: fmt(st.delta), d: st.totalP>0 ? pct((st.delta/st.totalP)*100) : (st.totalC>0?'New':'—'), cls: deltaCls(st.delta) }},
  ];
  // Always show 5 cards: 3 global + fill with segment snapshots for filtered or all
  const segs = st.segTotals;
  // If segment filter active, still show all 3 segment cards for context — total cards would be 6.
  // Requirement: 5 columns / 5 cards. Use: Current, Compare, Delta, then top-2 segment by |delta|? 
  // Better: Current, Compare, Resellers, End Users, OEM — put overall delta into each segment card.
  // Kevin asked 5 cards fitting width — original was Total2025, Total2026, 3 segments.
  // New model: Current, Compare, Resellers Δ, End Users Δ, OEM Δ  OR Current, Delta, 3 segments current.
  // Clearest 5: Current · Compare · Resellers · End Users · OEM
  const five = [
    {{ h: 'Current period', v: fmt(st.totalC), d: labelForKeys(st.currKeys), cls: 'muted' }},
    {{ h: 'Compare period', v: fmt(st.totalP), d: labelForKeys(st.cmpKeys) + ' · Δ ' + fmt(st.delta), cls: deltaCls(st.delta) }},
    ...segs.map(s => ({{
      h: s.label,
      v: fmt(s.current),
      d: `cmp ${{fmt(s.compare)}} · Δ ${{fmt(s.delta)}}`,
      cls: deltaCls(s.delta)
    }}))
  ];
  document.getElementById('kpis').innerHTML = five.map(c => `
    <div class="card">
      <h3>${{c.h}}</h3>
      <div class="val">${{c.v}}</div>
      <div class="delta ${{c.cls}}">${{c.d}}</div>
    </div>`).join('');

  document.getElementById('rangeLabel').textContent =
    `Current: ${{labelForKeys(st.currKeys)}}  ·  Compare: ${{labelForKeys(st.cmpKeys)}}  ·  Δ ${{fmt(st.delta)}}`;
}}

function headHTML(currLabel, cmpLabel) {{
  return `<tr>
    <th>#</th><th>Customer</th><th>Seg</th>
    <th>Compare</th><th>Current</th><th>Δ $</th><th>Δ %</th>
  </tr>`;
}}

function bodyHTML(rows, kind) {{
  return rows.map((r,i) => {{
    const key = r.customer + '|' + r.segment + '|' + kind;
    const sel = selectedKey === key ? 'selected' : '';
    const pill = SEG_PILL[r.segment] || '';
    const p = r.pct == null ? '<span class="new">New</span>' : `<span class="${{deltaCls(r.pct)}}">${{pct(r.pct)}}</span>`;
    return `<tr class="${{sel}}" data-idx="${{i}}">
      <td class="muted">${{i+1}}</td>
      <td class="name">${{r.customer}}</td>
      <td><span class="pill ${{pill}}">${{r.segmentLabel}}</span></td>
      <td>${{fmt(r.compare)}}</td>
      <td>${{fmt(r.current)}}</td>
      <td class="${{deltaCls(r.delta)}}">${{fmt(r.delta)}}</td>
      <td>${{p}}</td>
    </tr>`;
  }}).join('');
}}

function bindRows(sel, rows, kind) {{
  document.querySelectorAll(sel + ' tbody tr').forEach(tr => {{
    tr.onclick = () => {{
      const r = rows[Number(tr.dataset.idx)];
      selectedKey = r.customer + '|' + r.segment + '|' + kind;
      renderTables(window.__lastState);
      showDetail(r);
    }};
  }});
}}

function renderTables(st) {{
  window.__lastState = st;
  // sync tab active classes
  document.querySelectorAll('#segTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.seg===seg));
  document.querySelectorAll('#modeTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.mode===mode));

  document.querySelector('#accTable thead').innerHTML = headHTML();
  document.querySelector('#decTable thead').innerHTML = headHTML();
  document.querySelector('#newTable thead').innerHTML = headHTML();
  document.querySelector('#accTable tbody').innerHTML = bodyHTML(st.acc, 'acc');
  document.querySelector('#decTable tbody').innerHTML = bodyHTML(st.dec, 'dec');
  document.querySelector('#newTable tbody').innerHTML = bodyHTML(st.news, 'new');
  bindRows('#accTable', st.acc, 'acc');
  bindRows('#decTable', st.dec, 'dec');
  bindRows('#newTable', st.news, 'new');
}}

function showDetail(r) {{
  const el = document.getElementById('detail');
  el.classList.add('show');
  document.getElementById('detailTitle').textContent = r.customer;
  document.getElementById('detailMeta').textContent =
    `${{r.segmentLabel}} · compare ${{fmt(r.compare)}} · current ${{fmt(r.current)}} · Δ ${{fmt(r.delta)}} (${{r.pct==null?'New':pct(r.pct)}})`

  const series = DATA.facts
    .filter(f => f.c === r.customer && f.s === r.segment)
    .sort((a,b) => a.k - b.k);
  const labels = series.map(x => x.ym);
  const vals = series.map(x => x.v);
  const st = window.__lastState;
  const currSet = new Set(st.currKeys);
  const cmpSet = new Set(st.cmpKeys);
  const colors = series.map(x => currSet.has(x.k) ? 'rgba(91,157,255,.9)' : cmpSet.has(x.k) ? 'rgba(61,214,140,.55)' : 'rgba(139,155,176,.35)');

  const ctx = document.getElementById('detailChart');
  if (detailChart) detailChart.destroy();
  detailChart = new Chart(ctx, {{
    type: 'bar',
    data: {{ labels, datasets: [{{ label: 'Sales', data: vals, backgroundColor: colors, borderRadius: 4 }}] }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{ label: c => fmt(c.parsed.y) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b9bb0', maxRotation: 45 }}, grid: {{ display: false }} }},
        y: {{ ticks: {{ color: '#8b9bb0', callback: v => fmt(v) }}, grid: {{ color: 'rgba(36,48,65,.8)' }} }}
      }}
    }}
  }});
  el.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
}}

function renderCharts(st) {{
  const segs = st.segTotals;
  if (segChart) segChart.destroy();
  segChart = new Chart(document.getElementById('segChart'), {{
    type: 'bar',
    data: {{
      labels: segs.map(s => s.label),
      datasets: [
        {{ label: 'Compare', data: segs.map(s => s.compare), backgroundColor: 'rgba(139,155,176,.45)', borderRadius: 6 }},
        {{ label: 'Current', data: segs.map(s => s.current), backgroundColor: 'rgba(91,157,255,.85)', borderRadius: 6 }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '#c9d4e3' }} }},
        tooltip: {{ callbacks: {{ label: c => c.dataset.label + ': ' + fmt(c.parsed.y) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b9bb0' }}, grid: {{ display: false }} }},
        y: {{ ticks: {{ color: '#8b9bb0', callback: v => fmt(v) }}, grid: {{ color: 'rgba(36,48,65,.8)' }} }}
      }}
    }}
  }});

  const order = months.map(m => m.label);
  const colors = {{ D_R: '#5b9dff', End_User: '#3dd68c', OEM_KA: '#b388ff' }};
  const datasets = SEG_ORDER.map(segId => {{
    const map = Object.fromEntries(
      DATA.segmentMonth.filter(m => m.s === segId).map(m => [m.ym, m.v])
    );
    return {{
      label: DATA.segLabels[segId],
      data: order.map(ym => map[ym] || 0),
      borderColor: colors[segId],
      backgroundColor: colors[segId],
      tension: .25, pointRadius: 2, borderWidth: 2,
    }};
  }});
  if (monthChart) monthChart.destroy();
  monthChart = new Chart(document.getElementById('monthChart'), {{
    type: 'line',
    data: {{ labels: order, datasets }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ labels: {{ color: '#c9d4e3' }} }},
        tooltip: {{ callbacks: {{ label: c => c.dataset.label + ': ' + fmt(c.parsed.y) }} }}
      }},
      scales: {{
        x: {{ ticks: {{ color: '#8b9bb0', maxRotation: 45 }}, grid: {{ display: false }} }},
        y: {{ ticks: {{ color: '#8b9bb0', callback: v => fmt(v) }}, grid: {{ color: 'rgba(36,48,65,.8)' }} }}
      }}
    }}
  }});
}}

function renderAll() {{
  const st = compute();
  renderKpis(st);
  renderTables(st);
  renderCharts(st);
  if (!selectedKey) document.getElementById('detail').classList.remove('show');
}}

renderHeader();
initControls();
renderAll();
</script>
</body>
</html>
"""


def main():
    df = load_all()
    payload = build_payload(df)
    html = render_html(payload)
    for p in OUTS:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
        print("wrote", p, p.stat().st_size)
    print("months", len(payload["months"]), payload["months"][0], payload["months"][-1])
    print("facts", payload["meta"]["factCount"])


if __name__ == "__main__":
    main()
