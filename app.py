# -*- coding: utf-8 -*-
"""
Talent Demand Intelligence -- READ-ONLY dashboard over normalized Indian job-market postings.

Reads ONE slim Parquet (built by export_dashboard_data.py) via DuckDB. It NEVER connects to
Postgres and NEVER writes -- pure SELECT over a file. Every figure is an exact count from the
data. Each table is paired with a downloadable chart.

  streamlit run app.py
"""
import os
import json
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
PARQUET = os.path.join(HERE, "data", "jobs.parquet").replace("\\", "/")
GEOJSON = os.path.join(HERE, "data", "india_states.geojson")

st.set_page_config(page_title="Talent Demand Intelligence", page_icon="\U0001F4CA",
                   layout="wide", initial_sidebar_state="expanded")

# chart palette (single-accent magnitude + percentile trio)
ACCENT, ACCENT2, GOLD, MUTE = "#4d8dff", "#36d0b4", "#f4b740", "#7f8bad"

# ---------------------------------------------------------------- data access (read-only)
def _mtime():
    try:
        return os.path.getmtime(PARQUET)
    except OSError:
        return 0.0


@st.cache_resource
def _con(_v):
    c = duckdb.connect(database=":memory:")
    c.execute(f"CREATE VIEW jobs AS SELECT * FROM read_parquet('{PARQUET}')")
    return c


def con():
    return _con(_mtime())


@st.cache_data(show_spinner=False, max_entries=256)   # bound cache so memory stays flat
def q(sql, params, _v):
    return con().cursor().execute(sql, list(params)).df()


def run(sql, params=()):
    return q(sql, tuple(params), _mtime())


def one(sql, params=()):
    return con().cursor().execute(sql, list(params)).fetchone()


@st.cache_resource
def geojson():
    with open(GEOJSON, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- formatting
def grp(n):
    """Exact integer with thousands commas."""
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def inr(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    v = int(round(v))
    if v >= 10_000_000:
        return f"₹{v/10_000_000:.2f} Cr"
    if v >= 100_000:
        return f"₹{v/100_000:.2f} L"
    if v >= 1000:
        return f"₹{v/1000:.0f}k"
    return f"₹{v}"


# ---------------------------------------------------------------- styling
def css():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');
      :root{--bg:#06090f;--surf:#0b111c;--surf2:#0f1724;--line:rgba(255,255,255,.065);
            --line2:rgba(255,255,255,.11);--ink:#eef2f8;--mut:#828ca1;--mut2:#5e6880;
            --acc:#4d8dff;--acc2:#36d0b4;}
      .stApp{background:
        radial-gradient(1200px 500px at 80% -10%, rgba(77,141,255,.06), transparent 60%),
        radial-gradient(900px 400px at -5% 0%, rgba(54,208,180,.05), transparent 55%), #06090f;}
      html,body,[class*="css"]{font-family:'Inter',sans-serif;color:#eef2f8;}
      .block-container{padding-top:.6rem;padding-bottom:3rem;max-width:1580px;}
      #MainMenu,footer,header{visibility:hidden;}
      /* keep the Filters sidebar ALWAYS open -- not collapsible, so filters can never be lost */
      [data-testid="stSidebarCollapseButton"]{display:none !important;}
      section[data-testid="stSidebar"]{transform:none !important; visibility:visible !important;
        margin-left:0 !important; min-width:300px !important;}
      section[data-testid="stSidebar"][aria-expanded="false"]{width:300px !important;}
      section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"]{
        visibility:visible !important; display:flex !important;}
      section[data-testid="stSidebar"]{background:#080c13;border-right:1px solid var(--line);}
      section[data-testid="stSidebar"] .block-container{padding-top:1.2rem;}
      /* masthead */
      .mast{display:flex;align-items:center;gap:13px;padding:14px 2px 13px;margin-bottom:2px;
            border-bottom:1px solid var(--line);}
      .mark{width:34px;height:34px;border-radius:9px;flex:0 0 auto;
            background:linear-gradient(135deg,#4d8dff,#36d0b4);position:relative;box-shadow:0 0 22px rgba(77,141,255,.35);}
      .mark::after{content:"";position:absolute;inset:8px;border-radius:5px;
            background:#06090f;clip-path:polygon(0 70%,30% 40%,55% 62%,100% 12%,100% 100%,0 100%);}
      .mast h1{font-size:1.32rem;font-weight:800;letter-spacing:-.5px;margin:0;line-height:1.1;}
      .mast .sub{color:var(--mut);font-size:.78rem;margin-top:1px;}
      .mast .status{margin-left:auto;text-align:right;font-family:'JetBrains Mono',monospace;
            font-size:.68rem;color:var(--mut);line-height:1.6;}
      .mast .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#36d0b4;
            box-shadow:0 0 8px #36d0b4;margin-right:5px;vertical-align:middle;}
      /* KPI cards */
      .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(176px,1fr));gap:11px;margin:15px 0 4px;}
      .kpi{background:linear-gradient(180deg,#0e1624,#0a111c);border:1px solid var(--line);
           border-radius:13px;padding:15px 17px 14px;position:relative;overflow:hidden;}
      .kpi::before{content:"";position:absolute;top:0;left:14px;right:14px;height:1px;
           background:linear-gradient(90deg,transparent,rgba(77,141,255,.55),transparent);}
      .kpi .lbl{font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--mut);font-weight:600;}
      .kpi .val{font-size:1.62rem;font-weight:700;color:#f3f6fc;line-height:1.1;margin-top:7px;
                font-family:'JetBrains Mono',monospace;letter-spacing:-.5px;}
      .kpi .sub{font-size:.71rem;color:var(--mut);margin-top:4px;}
      /* note / section / caption */
      .note{background:linear-gradient(180deg,rgba(77,141,255,.07),rgba(77,141,255,.02));
            border:1px solid rgba(77,141,255,.22);border-left:2px solid #4d8dff;border-radius:9px;
            padding:10px 14px;font-size:.785rem;color:#aab4c8;margin:2px 0 12px;line-height:1.5;}
      .sec{font-size:.78rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
           color:#aeb8cc;margin:18px 0 6px;}
      .cap{font-size:.74rem;color:var(--mut);margin:-2px 0 9px;}
      /* tabs: minimal underline */
      .stTabs [data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid var(--line);}
      .stTabs [data-baseweb="tab"]{background:transparent;border-radius:0;padding:9px 15px;
           font-size:.8rem;font-weight:600;letter-spacing:.02em;color:var(--mut);}
      .stTabs [aria-selected="true"]{color:#fff;box-shadow:inset 0 -2px 0 #4d8dff;}
      /* dataframes */
      div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:11px;overflow:hidden;}
      .stDataFrame td,.stDataFrame th{font-variant-numeric:tabular-nums;}
      /* inputs */
      section[data-testid="stSidebar"] input{background:#0b121e !important;border-color:var(--line) !important;}
      .stRadio [data-baseweb="radio"]{font-size:.84rem;}
      /* download buttons: compact + unobtrusive */
      .stDownloadButton button{background:#0e1726;border:1px solid var(--line2);color:#aab4c8;
           font-size:.73rem;padding:3px 11px;border-radius:8px;}
      .stDownloadButton button:hover{border-color:var(--acc);color:#dfe6f3;}
    </style>""", unsafe_allow_html=True)


DARK = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c0c8da", family="Inter", size=12),
            margin=dict(l=6, r=10, t=44, b=6),
            title=dict(font=dict(size=14, color="#e9ecf5")),
            xaxis=dict(gridcolor="rgba(255,255,255,.055)", zerolinecolor="rgba(255,255,255,.08)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.055)", zerolinecolor="rgba(255,255,255,.08)"),
            legend=dict(font=dict(size=11)))

PLOT_CFG = {
    "displayModeBar": True, "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "zoom2d", "pan2d",
                               "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"],
    "toImageButtonOptions": {"format": "png", "filename": "talent_demand_chart", "scale": 2},
}


def sty(fig, color=None, clip=True):
    fig.update_layout(**DARK)
    if clip:   # cliponaxis only applies to cartesian traces (bar/scatter), not choropleth
        fig.update_traces(cliponaxis=False)      # keep value labels from clipping at the axis edge
    if color:
        fig.update_traces(marker_color=color)
    return fig


def show_chart(fig, key):
    # theme=None keeps our own Plotly styling (Streamlit's theme would override colors)
    st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CFG, key=key)


def dl_csv(df, fname, key, label="⬇ Download table (CSV)"):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"),
                       file_name=fname, mime="text/csv", key=key)


# ---------------------------------------------------------------- chart builders
def _clip(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def bar_h(df, cat, val, title, n=15, color=ACCENT):
    """Horizontal magnitude bar — biggest on top, direct value labels. Rendered full-width so
    long category labels have room (automargin fits them) and never collide with the bars."""
    d = df.head(n).copy()[::-1]
    headroom = float(d[val].max()) * 1.16 if len(d) else 1   # room for the outside value labels
    fig = go.Figure(go.Bar(
        y=[_clip(v, 34) for v in d[cat]], x=d[val], orientation="h",
        marker=dict(color=color), width=0.7,
        text=[f"{int(v):,}" for v in d[val]], textposition="outside",
        textfont=dict(color="#aab4c8", size=11), cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} postings<extra></extra>"))
    sty(fig)
    fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=13)),
                      height=max(300, 33 * len(d) + 92), bargap=0.3,
                      margin=dict(l=8, r=78, t=50, b=30))
    fig.update_xaxes(title_text="", range=[0, headroom])
    fig.update_yaxes(title_text="", automargin=True)
    return fig


def dumbbell(df, cat, title, n=12):
    """Percentile range per category: p25 — median — p75 (monthly ₹). The section header
    above the chart names it, so the figure carries NO title (keeps the legend clear)."""
    d = df.head(n).copy()[::-1]
    y = [_clip(v) for v in d[cat]]
    fig = go.Figure()
    for yy, a, b in zip(y, d["p25"], d["p75"]):
        fig.add_trace(go.Scatter(x=[a, b], y=[yy, yy], mode="lines",
                      line=dict(color="rgba(127,139,173,.5)", width=5),
                      hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=d["p25"], y=y, mode="markers", name="p25 (lower)",
                  marker=dict(color=MUTE, size=12),
                  hovertemplate="%{y}<br>p25 ₹%{x:,.0f}/mo<extra></extra>"))
    fig.add_trace(go.Scatter(x=d["p75"], y=y, mode="markers", name="p75 (upper)",
                  marker=dict(color=ACCENT2, size=12),
                  hovertemplate="%{y}<br>p75 ₹%{x:,.0f}/mo<extra></extra>"))
    fig.add_trace(go.Scatter(x=d["p50"], y=y, mode="markers", name="median",
                  marker=dict(color=GOLD, size=16, line=dict(color="#0b111c", width=1.6)),
                  hovertemplate="%{y}<br>median ₹%{x:,.0f}/mo<extra></extra>"))
    sty(fig)
    fig.update_layout(height=max(400, 48 * len(d) + 120),
                      margin=dict(l=16, r=40, t=54, b=70),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, xanchor="left",
                                  bgcolor="rgba(0,0,0,0)", font=dict(size=11),
                                  itemsizing="constant"))
    fig.update_xaxes(title=dict(text="monthly ₹", standoff=22), tickprefix="₹",
                     separatethousands=True, tickangle=0, automargin=True)
    fig.update_yaxes(title_text="", automargin=True, ticklabelstandoff=8)
    return fig


def trend_line(df, xcol, ycol, title):
    """Change-over-time: filled line, chronological left→right."""
    d = df.copy()
    fig = go.Figure(go.Scatter(
        x=d[xcol].astype(str), y=d[ycol], mode="lines+markers",
        line=dict(color=ACCENT, width=2.5), marker=dict(size=6, color=ACCENT),
        fill="tozeroy", fillcolor="rgba(77,141,255,.12)",
        hovertemplate="%{x}<br>%{y:,} postings<extra></extra>"))
    sty(fig)
    fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=13.5)),
                      height=400, margin=dict(l=16, r=18, t=52, b=96))
    fig.update_xaxes(title_text="", tickangle=-45, automargin=True, nticks=min(len(d), 14))
    fig.update_yaxes(title_text="postings", automargin=True)
    return fig


def india_map(df, title):
    """Choropleth of India shaded by posting volume per state."""
    fig = px.choropleth(
        df, geojson=geojson(), featureidkey="properties.ST_NM",
        locations="state", color="postings",
        color_continuous_scale=["#0d1b30", "#163a73", "#2f6ae0", "#4d8dff", "#86b4ff"])
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    sty(fig, clip=False)
    fig.update_traces(marker_line_color="rgba(255,255,255,.12)", marker_line_width=.5,
                      hovertemplate="<b>%{location}</b><br>%{z:,} postings<extra></extra>")
    fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=13.5)),
                      height=560, margin=dict(l=0, r=0, t=52, b=0),
                      coloraxis_colorbar=dict(title="postings", thickness=12, len=.7))
    return fig


def kpi_row(items):
    html = '<div class="kpis">'
    for lbl, val, sub in items:
        html += f'<div class="kpi"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- sidebar: filters
EXP_BANDS = ["Fresher", "0–1 yrs", "1–3 yrs", "3–5 yrs", "5–8 yrs", "8–12 yrs", "12+ yrs"]
css()
with st.sidebar:
    st.markdown("### \U0001F4CA Talent Demand Intelligence")
    st.markdown("#### Filters")
    families_all = [r[0] for r in con().cursor().execute(
        "SELECT DISTINCT job_family FROM jobs ORDER BY 1").fetchall()]
    sel_families = st.multiselect("Job family (L1)", families_all, placeholder="all job families")
    # L2 sub-categories, cascaded to the chosen L1 families (or all of them if none chosen)
    if sel_families:
        _ph = ",".join(["?"] * len(sel_families))
        subs_all = [r[0] for r in con().cursor().execute(
            f"SELECT DISTINCT sub_family FROM jobs WHERE job_family IN ({_ph}) ORDER BY 1",
            sel_families).fetchall()]
    else:
        subs_all = [r[0] for r in con().cursor().execute(
            "SELECT DISTINCT sub_family FROM jobs ORDER BY 1").fetchall()]
    sel_subs = st.multiselect("Sub-category (L2)", subs_all, placeholder="all sub-categories")
    kw = st.text_input("Title contains", placeholder="e.g. data engineer")
    f_company = st.text_input("Company contains", placeholder="any company…")
    f_role = st.text_input("Role contains", placeholder="any role…")
    f_city = st.text_input("City contains", placeholder="any city…")
    states_all = [r[0] for r in con().cursor().execute(
        "SELECT DISTINCT state FROM jobs WHERE state<>'(unknown)' ORDER BY 1").fetchall()]
    sel_states = st.multiselect("State", states_all, placeholder="all states")
    sectors_all = [r[0] for r in con().cursor().execute(
        "SELECT DISTINCT industry_sector FROM jobs WHERE industry_sector IS NOT NULL ORDER BY 1").fetchall()]
    sel_sectors = st.multiselect("Industry sector", sectors_all, placeholder="all sectors",
                                 help="Classified industry sector — available for ~7% of postings.")
    sel_exp = st.multiselect("Experience", EXP_BANDS, placeholder="all experience levels")
    sel_gender = st.multiselect("Gender preference", ["Male only", "Female only", "Any (Both)"],
                                placeholder="any gender preference",
                                help="Gender stated in the posting — specified on ~22% of postings.")
    # ---- date filter: All dates / Single day / Date range -------------------------------
    dmin, dmax = one("SELECT min(posted_on), max(posted_on) FROM jobs")
    dmin, dmax = pd.to_datetime(dmin).date(), pd.to_datetime(dmax).date()
    st.markdown("###### Posted date")
    date_mode = st.radio("Posting date filter", ["All dates", "Single day", "Date range"],
                         index=0, horizontal=True, label_visibility="collapsed")
    one_day = None
    date_range = None
    if date_mode == "Single day":
        one_day = st.date_input("Pick a day", value=dmax, min_value=dmin, max_value=dmax,
                                format="YYYY/MM/DD", help="Show postings from this exact date.")
    elif date_mode == "Date range":
        date_range = st.date_input("Pick a start and end date", value=(dmin, dmax),
                                   min_value=dmin, max_value=dmax, format="YYYY/MM/DD",
                                   help="Click a start date, then an end date. The filter applies "
                                        "once both are chosen.")
    wfh_only = st.checkbox("Work-from-home only")

# WHERE builder
where, p = ["1=1"], []
if kw:
    where.append("title ILIKE ?"); p.append(f"%{kw}%")
if f_company:
    where.append("company ILIKE ?"); p.append(f"%{f_company}%")
if f_role:
    where.append("role ILIKE ?"); p.append(f"%{f_role}%")
if f_city:
    where.append("city ILIKE ?"); p.append(f"%{f_city}%")
if sel_states:
    where.append(f"state IN ({','.join(['?']*len(sel_states))})"); p += sel_states
if sel_families:
    where.append(f"job_family IN ({','.join(['?']*len(sel_families))})"); p += sel_families
if sel_subs:
    where.append(f"sub_family IN ({','.join(['?']*len(sel_subs))})"); p += sel_subs
if sel_sectors:
    where.append(f"industry_sector IN ({','.join(['?']*len(sel_sectors))})"); p += sel_sectors
if sel_exp:
    where.append(f"exp_band IN ({','.join(['?']*len(sel_exp))})"); p += sel_exp
if sel_gender:
    where.append(f"gender_norm IN ({','.join(['?']*len(sel_gender))})"); p += sel_gender
# date filter (only narrows the data; otherwise null-date rows stay counted in totals)
if date_mode == "Single day" and one_day is not None:
    where.append("posted_on::date = ?"); p.append(one_day)
elif date_mode == "Date range" and isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    where.append("posted_on::date BETWEEN ? AND ?"); p += [date_range[0], date_range[1]]
if wfh_only:
    where.append("is_wfh = TRUE")
W = " AND ".join(where)
CITY_OK = "city NOT IN ('(unspecified)','Remote / WFH')"
ROLE_OK = "role <> '(not specified)'"
REAL_CO = ("company IS NOT NULL AND company<>'(not specified)' AND company NOT ILIKE '%confidential%' "
           "AND company NOT ILIKE '%on behalf%' AND lower(trim(company)) NOT IN "
           "('not mentioned','individual','not disclosed','company name','na','n/a','private','company',"
           "'employer','client of','hiring company','recruiter')")

# ---------------------------------------------------------------- masthead + KPIs
asof = pd.to_datetime(_mtime(), unit="s")
st.markdown(f"""<div class="mast"><div class="mark"></div>
  <div><h1>Talent Demand Intelligence</h1>
       <div class="sub">All-India job-market postings &nbsp;·&nbsp; normalized &amp; de-duplicated</div></div>
  <div class="status"><span class="dot"></span>live snapshot · {asof:%d %b %Y, %H:%M}<br>
       read-only · exact counts</div></div>""", unsafe_allow_html=True)

k = run(f"""SELECT count(*) jobs, count(DISTINCT company) comp, count(DISTINCT role) roles,
            count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities,
            count(DISTINCT state) FILTER(WHERE state<>'(unknown)') states,
            count(salary_monthly_min) sal_n,
            round(median(salary_monthly_min)) sal_med,
            min(posted_on::date) dmin, max(posted_on::date) dmax
            FROM jobs WHERE {W}""", p).iloc[0]

if int(k.jobs) == 0:
    st.warning("No records match these filters. Loosen them in the sidebar.")
    st.stop()

sal_cov = 100 * int(k.sal_n) / int(k.jobs)
kpi_row([
    ("Job postings", grp(k.jobs), "matching your filters"),
    ("Hiring companies", grp(k.comp), "distinct employers"),
    ("Distinct roles", grp(k.roles), "job titles / roles"),
    ("Cities · States", f"{grp(k.cities)} · {int(k.states)}", "normalized geography"),
    ("Median pay (mo.)", inr(k.sal_med), f"from {sal_cov:.0f}% that disclose"),
    ("Date coverage", f"{pd.to_datetime(k.dmin):%b %Y}–{pd.to_datetime(k.dmax):%b %Y}", "posting dates"),
])

tabs = st.tabs(["Overview", "Compensation", "Demand", "Geography", "Hiring trends",
                "Employers", "Job records"])

# ================================================================ OVERVIEW
with tabs[0]:
    st.markdown('<div class="note">Exact counts of job postings, de-duplicated by posting id. Each '
                'chart is downloadable (hover → camera icon); tables download as CSV. The sidebar '
                'filters apply everywhere. "(not specified)"/placeholder buckets are excluded from '
                'these ranked lists but remain in the totals above.</div>', unsafe_allow_html=True)

    def rank_df(dim, label, ok, extra_cols=True):
        extra = (", count(DISTINCT company) employers, count(DISTINCT city) FILTER(WHERE {c}) cities, "
                 "round(median(salary_monthly_min)) median_pay").format(c=CITY_OK) if extra_cols else \
                ", count(DISTINCT company) employers, round(median(salary_monthly_min)) median_pay"
        df = run(f"""SELECT {dim} AS "{label}", count(*) postings{extra}
                     FROM jobs WHERE {W} AND {ok} GROUP BY 1 ORDER BY postings DESC LIMIT 50""", p)
        return df

    def panel(title, df, cat, fname, key, color=ACCENT):
        st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)
        if len(df):
            show_chart(bar_h(df, cat, "postings", f"Top 15 · {title.lower()}", color=color), key=f"ch_{key}")
        disp = df.copy()
        if "median_pay" in disp:
            disp["median_pay"] = disp["median_pay"].map(inr)
        st.dataframe(disp, use_container_width=True, hide_index=True, height=360)
        dl_csv(df, fname, key=f"dl_{key}")

    # full-width panels (chart + table stacked) so nothing is cramped
    panel("Most in-demand roles", rank_df("role", "role", ROLE_OK), "role",
          "top_roles.csv", "ov_roles")
    panel("Top hiring cities", rank_df("city", "city", CITY_OK, extra_cols=False), "city",
          "top_cities.csv", "ov_cities", color=ACCENT2)
    emp = run(f"""SELECT company, count(*) postings, count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities,
                 count(DISTINCT role) roles, round(median(salary_monthly_min)) median_pay
                 FROM jobs WHERE {W} AND {REAL_CO} GROUP BY 1 ORDER BY postings DESC LIMIT 50""", p)
    panel("Most active employers", emp, "company", "top_employers.csv", "ov_emp", color=GOLD)
    stt = run(f"""SELECT state AS "state", count(*) postings,
                 count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities, count(DISTINCT company) employers,
                 round(median(salary_monthly_min)) median_pay
                 FROM jobs WHERE {W} AND state<>'(unknown)' GROUP BY 1 ORDER BY postings DESC LIMIT 40""", p)
    panel("Demand by state", stt, "state", "demand_by_state.csv", "ov_state", color=ACCENT2)

# ================================================================ COMPENSATION
with tabs[1]:
    st.markdown('<div class="note">Pay is normalized to <b>monthly ₹</b> for comparability '
                '(postings quoting an annual figure are divided by 12). Values of 0 = "not disclosed" '
                '(excluded); figures clipped to ₹3k–₹50L/month to drop junk. '
                '<b>p25 / median / p75</b> = 25th / 50th / 75th percentile.</div>', unsafe_allow_html=True)
    cov = run(f"""SELECT count(*) n, count(salary_monthly_min) disc,
                  round(quantile_cont(salary_monthly_min,0.25)) p25,
                  round(quantile_cont(salary_monthly_min,0.50)) p50,
                  round(quantile_cont(salary_monthly_min,0.75)) p75
                  FROM jobs WHERE {W}""", p).iloc[0]
    dr = 100*int(cov.disc)/max(int(cov.n), 1)
    kpi_row([
        ("Postings with pay", grp(cov.disc), f"{dr:.0f}% disclosure rate"),
        ("p25 monthly", inr(cov.p25), "lower quartile"),
        ("Median monthly", inr(cov.p50), "50th percentile"),
        ("p75 monthly", inr(cov.p75), "upper quartile"),
    ])
    dim = st.radio("Break pay down by",
                   ["Job family", "Sub-category", "Role", "City", "Experience band", "Industry sector"],
                   horizontal=True)
    col = {"Job family": "job_family", "Sub-category": "sub_family", "Role": "role", "City": "city",
           "Experience band": None, "Industry sector": "industry_sector"}[dim]
    if dim == "Experience band":
        q_ = f"""SELECT exp_band band,
                 count(salary_monthly_min) n,
                 round(quantile_cont(salary_monthly_min,0.25)) p25,
                 round(quantile_cont(salary_monthly_min,0.50)) p50,
                 round(quantile_cont(salary_monthly_min,0.75)) p75
                 FROM jobs WHERE {W} AND salary_monthly_min IS NOT NULL AND exp_band<>'Not specified' GROUP BY 1
                 ORDER BY CASE band WHEN 'Fresher' THEN 0 WHEN '0–1 yrs' THEN 1 WHEN '1–3 yrs' THEN 2
                                    WHEN '3–5 yrs' THEN 3 WHEN '5–8 yrs' THEN 4 WHEN '8–12 yrs' THEN 5
                                    WHEN '12+ yrs' THEN 6 ELSE 7 END"""
        df = run(q_, p)
        xcol = "band"
        ordered = True
    else:
        ok = {"role": ROLE_OK, "city": CITY_OK, "job_family": "1=1",
              "sub_family": "1=1", "industry_sector": "industry_sector IS NOT NULL"}[col]
        df = run(f"""SELECT {col} AS "{col}", count(salary_monthly_min) n,
                     round(quantile_cont(salary_monthly_min,0.25)) p25,
                     round(quantile_cont(salary_monthly_min,0.50)) p50,
                     round(quantile_cont(salary_monthly_min,0.75)) p75
                     FROM jobs WHERE {W} AND salary_monthly_min IS NOT NULL AND {ok}
                     GROUP BY 1 HAVING count(salary_monthly_min)>=30 ORDER BY n DESC LIMIT 18""", p)
        xcol = col
        ordered = False
    if len(df):
        st.markdown(f'<div class="sec">Monthly ₹ pay by {dim.lower()}</div>', unsafe_allow_html=True)
        # dumbbell wants the strongest groups; for experience keep the natural band order
        chart_df = df if ordered else df.head(16)
        show_chart(dumbbell(chart_df, xcol, f"Pay range (p25–median–p75) by {dim.lower()}"), key="cmp_db")
        disp = df.copy()
        for cc in ("p25", "p50", "p75"):
            disp[cc] = disp[cc].map(inr)
        disp = disp.rename(columns={"n": "postings w/ pay", "p25": "p25 /mo", "p50": "median /mo", "p75": "p75 /mo"})
        st.dataframe(disp, use_container_width=True, hide_index=True, height=460)
        dl_csv(df, "pay_by_%s.csv" % col if col else "pay_by_experience.csv", key="cmp_dl")
        st.markdown('<div class="cap">Only groups with ≥30 disclosed salaries are shown, so the '
                    'percentiles are statistically stable. The dot is the median; the bar spans p25–p75.</div>',
                    unsafe_allow_html=True)
    else:
        st.info("Not enough disclosed salaries in this selection to compute stable percentiles.")

# ================================================================ DEMAND
with tabs[2]:
    def explorer(dim, label, ok, color=ACCENT):
        st.markdown(f'<div class="sec">All {label} (complete — search any value)</div>', unsafe_allow_html=True)
        find = st.text_input(f"Search {label}", key=f"s_{dim}", placeholder=f"type any {label[:-1]}…")
        w2, p2 = f"{W} AND {ok}", list(p)
        if find:
            w2 += f" AND {dim} ILIKE ?"; p2 += [f"%{find}%"]
        total = one(f"SELECT count(DISTINCT {dim}) FROM jobs WHERE {w2}", p2)[0]
        if not total and not find:
            st.info(f"This field isn’t available for the current selection. Clear some filters to see it.")
            return
        df = run(f"""SELECT {dim} AS "{label[:-1]}", count(*) postings,
                     count(DISTINCT company) employers,
                     count(salary_monthly_min) with_pay,
                     round(median(salary_monthly_min)) median_monthly
                     FROM jobs WHERE {w2} GROUP BY 1 ORDER BY postings DESC LIMIT 500""", p2)
        if len(df):
            show_chart(bar_h(df, label[:-1], "postings", f"Top 15 · {label}", color=color), key=f"dm_ch_{dim}")
        dfd = df.copy()
        dfd["median_monthly"] = dfd["median_monthly"].map(inr)
        st.caption(f"{total:,} distinct {label} match — top 500 by postings (search to reach any one).")
        st.dataframe(dfd, use_container_width=True, hide_index=True, height=380)
        dl_csv(df, f"{label.replace(' ', '_')}.csv", key=f"dm_dl_{dim}")

    sub = st.radio("Dimension", ["Roles", "Industry sector", "Skills", "Gender", "Work type"], horizontal=True)
    if sub == "Roles":
        explorer("role", "roles", ROLE_OK)
    elif sub == "Gender":
        st.markdown('<div class="note">Gender preference <b>as stated in the posting</b> — specified on '
                    'about ~22% of postings (the rest state no preference). A sobering look at hiring '
                    'bias in the market.</div>', unsafe_allow_html=True)
        gdf = run(f"""SELECT gender_norm AS "gender preference", count(*) postings,
                      count(DISTINCT company) employers, count(salary_monthly_min) with_pay,
                      round(median(salary_monthly_min)) median_monthly
                      FROM jobs WHERE {W} GROUP BY 1 ORDER BY postings DESC""", p)
        if len(gdf):
            show_chart(bar_h(gdf, "gender preference", "postings", "Postings by stated gender preference",
                             n=10, color=GOLD), key="dm_gender")
        gdisp = gdf.copy()
        gdisp["median_monthly"] = gdisp["median_monthly"].map(inr)
        st.dataframe(gdisp, use_container_width=True, hide_index=True)
        dl_csv(gdf, "gender_preference.csv", key="dm_dl_gender")
    elif sub == "Industry sector":
        st.markdown('<div class="note">A classified <b>industry sector</b> is available for ~7% of '
                    'postings. Broader job categories are reflected in the Job family / Sub-category '
                    'instead.</div>', unsafe_allow_html=True)
        explorer("industry_sector", "industry sectors", "industry_sector IS NOT NULL", color=ACCENT2)
    elif sub == "Skills":
        st.markdown('<div class="note">Skills are free-text and present on ~38% of postings. '
                    'Shown as provided, exact counts.</div>', unsafe_allow_html=True)
        explorer("skills", "skills", "skills IS NOT NULL AND skills<>''", color=ACCENT2)
    else:
        df = run(f"""SELECT coalesce(employment_type_norm,'(unspecified)') AS "work type", count(*) postings
                     FROM jobs WHERE {W} GROUP BY 1 ORDER BY postings DESC LIMIT 12""", p)
        if len(df):
            show_chart(bar_h(df, "work type", "postings", "Postings by work type", n=10, color=ACCENT),
                       key="dm_worktype")
        st.dataframe(df, use_container_width=True, hide_index=True)
        dl_csv(df, "work_type.csv", key="dm_dl_worktype")
        wfh = run(f"SELECT count(*) FILTER(WHERE is_wfh) w, count(*) n FROM jobs WHERE {W}", p).iloc[0]
        st.markdown(f'<div class="cap">Work-from-home flag set on {grp(wfh.w)} of {grp(wfh.n)} postings '
                    f'({100*int(wfh.w)/max(int(wfh.n),1):.1f}%). WFH is flagged on only a subset of '
                    f'postings, so this undercounts true remote roles.</div>', unsafe_allow_html=True)

# ================================================================ GEOGRAPHY
with tabs[3]:
    st.markdown('<div class="note">City & state are normalized from each posting’s raw location '
                '(e.g. "Bengaluru/Bangalore", "Whitefield, Bangalore" → <b>Bengaluru, Karnataka</b>). '
                'Raw location is retained in the Job records tab.</div>', unsafe_allow_html=True)
    mp = run(f"""SELECT state, count(*) postings FROM jobs
                 WHERE {W} AND state<>'(unknown)' GROUP BY 1 ORDER BY 2 DESC""", p)
    if len(mp):
        st.markdown('<div class="sec">Postings across India</div>', unsafe_allow_html=True)
        show_chart(india_map(mp, "Job postings by state"), key="geo_map")
        dl_csv(mp, "postings_by_state.csv", key="geo_dl_state")
    c1, c2 = st.columns([3, 2])
    with c1:
        df = run(f"""SELECT city, any_value(state) AS "state", count(*) postings,
                     count(DISTINCT company) employers, round(median(salary_monthly_min)) median_monthly
                     FROM jobs WHERE {W} AND {CITY_OK} GROUP BY 1 ORDER BY postings DESC LIMIT 400""", p)
        tot = one(f"SELECT count(DISTINCT city) FROM jobs WHERE {W} AND {CITY_OK}", p)[0]
        st.markdown('<div class="sec">Top cities</div>', unsafe_allow_html=True)
        if len(df):
            show_chart(bar_h(df, "city", "postings", "Top 15 cities by postings", color=ACCENT2),
                       key="geo_cities_ch")
        dfd = df.copy()
        dfd["median_monthly"] = dfd["median_monthly"].map(inr)
        st.caption(f"{tot:,} normalized cities — top 400 by postings.")
        st.dataframe(dfd, use_container_width=True, hide_index=True, height=440)
        dl_csv(df, "top_cities_full.csv", key="geo_dl_city")
    with c2:
        dfs = run(f"""SELECT state AS "state", count(*) postings, count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities
                      FROM jobs WHERE {W} AND state<>'(unknown)' GROUP BY 1 ORDER BY postings DESC""", p)
        st.markdown('<div class="sec">States</div>', unsafe_allow_html=True)
        st.caption(f"{len(dfs)} states · covers {int(k.states)} with known geography.")
        st.dataframe(dfs, use_container_width=True, hide_index=True, height=440)
        dl_csv(dfs, "states.csv", key="geo_dl_states2")

# ================================================================ HIRING TRENDS
with tabs[4]:
    cc1, cc2 = st.columns([1, 1])
    with cc1:
        g = st.radio("Granularity", ["Daily", "Weekly", "Monthly"], index=1, horizontal=True, key="gran")
    with cc2:
        if g == "Daily":
            win = st.radio("Window", ["7 days", "14 days", "30 days", "90 days"], index=1, horizontal=True, key="wind")
            days = {"7 days": 7, "14 days": 14, "30 days": 30, "90 days": 90}[win]
        else:
            win = st.radio("Window", ["12 weeks", "26 weeks", "52 weeks", "All"], index=1, horizontal=True, key="winw")
            days = {"12 weeks": 84, "26 weeks": 182, "52 weeks": 364, "All": None}[win]
    Wt, pt = f"{W} AND posted_on IS NOT NULL", list(p)
    if days:
        Wt += " AND posted_on::date >= ?"; pt.append(dmax - pd.Timedelta(days=days))
    # format the period as a clean date string (no 00:00:00 time); ISO keeps it sortable
    if g == "Daily":
        per = "strftime(posted_on, '%Y-%m-%d')"
    elif g == "Weekly":
        per = "'Week of ' || strftime(date_trunc('week', posted_on), '%Y-%m-%d')"
    else:
        per = "strftime(date_trunc('month', posted_on), '%Y-%m')"
    label = "day" if g == "Daily" else ("week" if g == "Weekly" else "month")
    st.markdown('<div class="note">Job postings counted by their <b>posting date</b>, newest first. '
                'Weekly/monthly rows are labelled by the <b>start</b> of that week/month. '
                'The latest period is partial (still in progress), so it reads low. '
                '<b>change</b> = vs. the previous period.</div>', unsafe_allow_html=True)
    if g == "Daily":
        df = run(f"SELECT {per} AS date, dayname(posted_on) AS weekday, count(*) postings "
                 f"FROM jobs WHERE {Wt} GROUP BY 1,2 ORDER BY 1", pt)
        key_col = "date"
    else:
        df = run(f"SELECT {per} AS period, count(*) postings FROM jobs WHERE {Wt} GROUP BY 1 ORDER BY 1", pt)
        key_col = "period"
    if len(df):
        show_chart(trend_line(df, key_col, "postings", f"Postings per {label} · {win}"), key="trend_ch")
        tbl = df.copy()
        tbl["change"] = tbl["postings"].pct_change().map(lambda v: f"{v*100:+.0f}%" if pd.notna(v) else "—")
        tbl = tbl.iloc[::-1].reset_index(drop=True)
        st.markdown(f'<div class="sec">Postings per {label} · {win}</div>', unsafe_allow_html=True)
        st.dataframe(tbl, use_container_width=True, hide_index=True, height=420)
        dl_csv(tbl, f"postings_per_{label}.csv", key="trend_dl")

# ================================================================ EMPLOYERS
with tabs[5]:
    st.markdown('<div class="note">Employer names are shown <b>exactly as posted</b> (not merged or '
                'cleaned). Placeholder names ("Not mentioned", "Individual", staffing-confidential) are '
                'excluded from this ranked view but remain in the job records.</div>', unsafe_allow_html=True)
    find = st.text_input("Search company", key="s_emp", placeholder="type any company…")
    w2, p2 = f"{W} AND {REAL_CO}", list(p)
    if find:
        w2 += " AND company ILIKE ?"; p2 += [f"%{find}%"]
    total = one(f"SELECT count(DISTINCT company) FROM jobs WHERE {w2}", p2)[0]
    df = run(f"""SELECT company, count(*) postings, count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities,
                 count(DISTINCT role) roles, round(median(salary_monthly_min)) median_monthly
                 FROM jobs WHERE {w2} GROUP BY 1 ORDER BY postings DESC LIMIT 500""", p2)
    if len(df):
        show_chart(bar_h(df, "company", "postings", "Top 15 most active employers", color=GOLD),
                   key="emp_ch")
    dfd = df.copy()
    dfd["median_monthly"] = dfd["median_monthly"].map(inr)
    st.caption(f"{total:,} distinct named employers match — top 500 by postings.")
    st.dataframe(dfd, use_container_width=True, hide_index=True, height=460)
    dl_csv(df, "employers.csv", key="emp_dl")

# ================================================================ JOB RECORDS
with tabs[6]:
    st.caption(f"{grp(k.jobs)} postings match. Showing the 1,000 most recent; download the full "
               f"filtered set below.")
    rows = run(f"""SELECT title, company, city, state, job_family, sub_family, role,
                   industry_sector, salary_monthly_min, salary_monthly_max, experience, exp_band,
                   employment_type_norm AS work_type, is_wfh, posted_on
                   FROM jobs WHERE {W} ORDER BY posted_on DESC NULLS LAST LIMIT 1000""", p)
    st.dataframe(rows, use_container_width=True, hide_index=True, height=560, column_config={
        "posted_on": st.column_config.DatetimeColumn("posted", format="YYYY-MM-DD"),
        "salary_monthly_min": st.column_config.NumberColumn("pay min/mo", format="₹%d"),
        "salary_monthly_max": st.column_config.NumberColumn("pay max/mo", format="₹%d")})
    # build the full CSV only on demand (keeps memory flat; 1M+ rows aren't materialized on every view)
    if st.checkbox(f"Prepare download of all {grp(k.jobs)} filtered records"):
        full = con().cursor().execute(f"""SELECT title, company, city, state, location,
                   job_family, sub_family, role, industry, industry_sector,
                   salary_min, salary_max, salary_monthly_min, salary_monthly_max,
                   experience, exp_min_years, exp_max_years, exp_band,
                   employment_type, employment_type_norm, education, skills, is_wfh, posted_on
                   FROM jobs WHERE {W} ORDER BY posted_on DESC NULLS LAST""", p).df()
        st.download_button(f"⬇ Download CSV ({grp(len(full))} rows)",
                           full.to_csv(index=False).encode("utf-8"),
                           file_name="talent_demand.csv", mime="text/csv")
