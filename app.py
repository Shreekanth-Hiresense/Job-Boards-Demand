# -*- coding: utf-8 -*-
"""
Talent Demand Intelligence -- READ-ONLY dashboard over the scraped Indian job-board data.

Reads ONE slim Parquet (built by export_dashboard_data.py) via DuckDB. It NEVER connects to
Postgres and NEVER writes -- pure SELECT over a file. Every figure is an exact count from the
data; coverage and methodology are shown openly so nothing has to be taken on trust.

  streamlit run app.py
"""
import os
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
PARQUET = os.path.join(HERE, "data", "jobs.parquet").replace("\\", "/")

st.set_page_config(page_title="Talent Demand Intelligence", page_icon="\U0001F4CA",
                   layout="wide", initial_sidebar_state="expanded")

INK = ["#4f8cff", "#2bd4a7", "#f4b740", "#ff6b81", "#9b7bff", "#38bdf8", "#f97316", "#a3e635"]

BOARDS = {
    "All boards": dict(key=None,        tag="every source combined", unit="mixed"),
    "Apna":       dict(key="apna",      tag="entry-level / blue-collar · apna.co API", unit="monthly"),
    "WorkIndia":  dict(key="workindia", tag="blue-collar · workindia.in", unit="monthly"),
    "Jobhai":     dict(key="jobhai",    tag="blue & grey-collar · jobhai.com", unit="monthly"),
    "NCS":        dict(key="ncs",       tag="Govt National Career Service", unit="annual"),
    "Foundit":    dict(key="foundit",   tag="white-collar · foundit.in", unit="annual"),
    "Quikr":      dict(key="quikr",     tag="classifieds · quikr.com", unit="monthly"),
}

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
    return con().execute(sql, list(params)).df()


def run(sql, params=()):
    return q(sql, tuple(params), _mtime())


def one(sql, params=()):
    return con().execute(sql, list(params)).fetchone()


# ---------------------------------------------------------------- formatting
def grp(n):
    """Exact integer with Indian-style readability via thousands commas."""
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
      /* sidebar as a control panel */
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
      /* radio -> nav list */
      section[data-testid="stSidebar"] [role="radiogroup"]{gap:1px;}
      section[data-testid="stSidebar"] [role="radiogroup"] label{padding:3px 0;border-radius:7px;}
      /* dataframes */
      div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:11px;overflow:hidden;}
      .stDataFrame td,.stDataFrame th{font-variant-numeric:tabular-nums;}
      /* inputs */
      section[data-testid="stSidebar"] input{background:#0b121e !important;border-color:var(--line) !important;}
      .stRadio [data-baseweb="radio"]{font-size:.84rem;}
    </style>""", unsafe_allow_html=True)


DARK = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c0c8da", family="Inter", size=12),
            margin=dict(l=6, r=10, t=44, b=6),
            title=dict(font=dict(size=14, color="#e9ecf5")),
            xaxis=dict(gridcolor="rgba(255,255,255,.055)", zerolinecolor="rgba(255,255,255,.08)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.055)", zerolinecolor="rgba(255,255,255,.08)"),
            legend=dict(font=dict(size=11)))


def sty(fig, color=None):
    fig.update_layout(**DARK)
    fig.update_traces(cliponaxis=False)          # keep value labels from clipping at the axis edge
    if color:
        fig.update_traces(marker_color=color)
    return fig


def kpi_row(items):
    html = '<div class="kpis">'
    for lbl, val, sub in items:
        html += f'<div class="kpi"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- sidebar: board + filters
css()
with st.sidebar:
    st.markdown("### \U0001F4CA Talent Demand Intelligence")
    board_name = st.radio("Source", list(BOARDS.keys()))
    B = BOARDS[board_name]
    st.divider()
    st.markdown("#### Filters")
    kw = st.text_input("Title contains", placeholder="e.g. data engineer")
    f_company = st.text_input("Company contains", placeholder="any company…")
    f_role = st.text_input("Role contains", placeholder="any role…")
    f_city = st.text_input("City contains", placeholder="any city…")
    states_all = [r[0] for r in con().execute(
        "SELECT DISTINCT state FROM jobs WHERE state<>'(unknown)' ORDER BY 1").fetchall()]
    sel_states = st.multiselect("State", states_all, placeholder="all states")
    dmin, dmax = one("SELECT min(posted_on), max(posted_on) FROM jobs")
    dmin, dmax = pd.to_datetime(dmin).date(), pd.to_datetime(dmax).date()
    date_range = st.date_input("Posted between", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    exp_hi = st.slider("Max experience (yrs)", 0, 30, 30)
    wfh_only = st.checkbox("Work-from-home only")

# WHERE builder
where, p = ["1=1"], []
if B["key"]:
    where.append("board = ?"); p.append(B["key"])
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
if (isinstance(date_range, (list, tuple)) and len(date_range) == 2
        and (date_range[0] != dmin or date_range[1] != dmax)):   # only filter if narrowed (keeps null-date rows in totals)
    where.append("posted_on::date BETWEEN ? AND ?"); p += [date_range[0], date_range[1]]
if exp_hi < 30:
    where.append("(exp_years IS NULL OR exp_years <= ?)"); p.append(exp_hi)
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
       <div class="sub">{board_name} &nbsp;·&nbsp; {B['tag']}</div></div>
  <div class="status"><span class="dot"></span>live snapshot · {asof:%d %b %Y, %H:%M}<br>
       read-only · exact counts from source</div></div>""", unsafe_allow_html=True)

k = run(f"""SELECT count(*) jobs, count(DISTINCT company) comp, count(DISTINCT role) roles,
            count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities,
            count(DISTINCT state) FILTER(WHERE state<>'(unknown)') states,
            count(salary_monthly_min) sal_n,
            round(median(salary_monthly_min)) sal_med,
            min(posted_on::date) dmin, max(posted_on::date) dmax, count(DISTINCT board) brds
            FROM jobs WHERE {W}""", p).iloc[0]

if int(k.jobs) == 0:
    st.warning("No records match these filters. Loosen them in the sidebar.")
    st.stop()

sal_cov = 100 * int(k.sal_n) / int(k.jobs)
kpi_row([
    ("Job postings", grp(k.jobs), f"{board_name}"),
    ("Hiring companies", grp(k.comp), "distinct employers"),
    ("Distinct roles", grp(k.roles), "job titles / roles"),
    ("Cities · States", f"{grp(k.cities)} · {int(k.states)}", "normalized geography"),
    ("Median pay (mo.)", inr(k.sal_med), f"from {sal_cov:.0f}% that disclose"),
    ("Date coverage", f"{pd.to_datetime(k.dmin):%b %Y}–{pd.to_datetime(k.dmax):%b %Y}", "posting dates"),
])

tabs = st.tabs(["Overview", "Compensation", "Demand", "Geography", "Hiring trends",
                "Employers", "Data & methodology", "Job records"])

# ================================================================ OVERVIEW
with tabs[0]:
    st.markdown('<div class="note">Exact counts of job postings from the sources, de-duplicated by job id. '
                'Click any column header to sort. The sidebar filters — including <b>Company contains</b> '
                '— apply to every table here. "(not specified)"/placeholder buckets are excluded from these '
                'ranked lists but remain in the totals above.</div>', unsafe_allow_html=True)

    def rank(dim, label, ok, extra_cols=True):
        extra = (", count(DISTINCT company) employers, count(DISTINCT city) FILTER(WHERE {c}) cities, "
                 "round(median(salary_monthly_min)) median_pay").format(c=CITY_OK) if extra_cols else \
                ", count(DISTINCT company) employers, round(median(salary_monthly_min)) median_pay"
        df = run(f"""SELECT {dim} AS "{label}", count(*) postings{extra}
                     FROM jobs WHERE {W} AND {ok} GROUP BY 1 ORDER BY postings DESC LIMIT 50""", p)
        if "median_pay" in df:
            df["median_pay"] = df["median_pay"].map(inr)
        st.dataframe(df, use_container_width=True, hide_index=True, height=420)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec">Most in-demand roles</div>', unsafe_allow_html=True)
        rank("role", "role", ROLE_OK)
    with c2:
        st.markdown('<div class="sec">Top hiring cities</div>', unsafe_allow_html=True)
        rank("city", "city", CITY_OK, extra_cols=False)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec">Most active employers</div>', unsafe_allow_html=True)
        df = run(f"""SELECT company, count(*) postings, count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities,
                     count(DISTINCT role) roles, round(median(salary_monthly_min)) median_pay
                     FROM jobs WHERE {W} AND {REAL_CO} GROUP BY 1 ORDER BY postings DESC LIMIT 50""", p)
        df["median_pay"] = df["median_pay"].map(inr)
        st.dataframe(df, use_container_width=True, hide_index=True, height=420)
    with c2:
        st.markdown('<div class="sec">Demand by state</div>', unsafe_allow_html=True)
        df = run(f"""SELECT state AS "state", count(*) postings,
                     count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities, count(DISTINCT company) employers,
                     round(median(salary_monthly_min)) median_pay
                     FROM jobs WHERE {W} AND state<>'(unknown)' GROUP BY 1 ORDER BY postings DESC LIMIT 40""", p)
        df["median_pay"] = df["median_pay"].map(inr)
        st.dataframe(df, use_container_width=True, hide_index=True, height=420)

# ================================================================ COMPENSATION
with tabs[1]:
    st.markdown('<div class="note">Pay is normalized to <b>monthly ₹</b> for comparability '
                '(apna/workindia/jobhai/quikr are monthly; foundit/ncs are annual → ÷12). '
                'Values of 0 = "not disclosed" (excluded); figures clipped to ₹1k–₹50L/month to drop junk. '
                '<b>p25 / p50 / p75</b> = 25th / median / 75th percentile.</div>', unsafe_allow_html=True)
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
    dim = st.radio("Break pay down by", ["Role", "City", "Experience band", "Board"], horizontal=True)
    col = {"Role": "role", "City": "city", "Experience band": None, "Board": "board"}[dim]
    if dim == "Experience band":
        q_ = f"""SELECT CASE
                   WHEN exp_years IS NULL THEN '(unknown)'
                   WHEN exp_years<2 THEN '0-2 yrs' WHEN exp_years<5 THEN '2-5 yrs'
                   WHEN exp_years<8 THEN '5-8 yrs' WHEN exp_years<12 THEN '8-12 yrs'
                   ELSE '12+ yrs' END band,
                 count(salary_monthly_min) n,
                 round(quantile_cont(salary_monthly_min,0.25)) p25,
                 round(quantile_cont(salary_monthly_min,0.50)) p50,
                 round(quantile_cont(salary_monthly_min,0.75)) p75
                 FROM jobs WHERE {W} AND salary_monthly_min IS NOT NULL GROUP BY 1
                 ORDER BY CASE band WHEN '0-2 yrs' THEN 1 WHEN '2-5 yrs' THEN 2 WHEN '5-8 yrs' THEN 3
                                    WHEN '8-12 yrs' THEN 4 WHEN '12+ yrs' THEN 5 ELSE 6 END"""
        df = run(q_, p)
        xcol = "band"
    else:
        ok = {"role": ROLE_OK, "city": CITY_OK, "board": "1=1"}[col]
        df = run(f"""SELECT {col} AS "{col}", count(salary_monthly_min) n,
                     round(quantile_cont(salary_monthly_min,0.25)) p25,
                     round(quantile_cont(salary_monthly_min,0.50)) p50,
                     round(quantile_cont(salary_monthly_min,0.75)) p75
                     FROM jobs WHERE {W} AND salary_monthly_min IS NOT NULL AND {ok}
                     GROUP BY 1 HAVING count(salary_monthly_min)>=30 ORDER BY n DESC LIMIT 18""", p)
        xcol = col
    if len(df):
        disp = df.copy()
        for cc in ("p25", "p50", "p75"):
            disp[cc] = disp[cc].map(inr)
        disp = disp.rename(columns={"n": "postings w/ pay", "p25": "p25 /mo", "p50": "median /mo", "p75": "p75 /mo"})
        st.markdown(f'<div class="sec">Monthly ₹ pay by {dim.lower()}</div>', unsafe_allow_html=True)
        st.dataframe(disp, use_container_width=True, hide_index=True, height=560)
        st.markdown('<div class="cap">Sorted by number of postings. Only groups with ≥30 disclosed '
                    'salaries are shown, so the percentiles are statistically stable. Click a header to re-sort.</div>',
                    unsafe_allow_html=True)
    else:
        st.info("Not enough disclosed salaries in this selection to compute stable percentiles.")

# ================================================================ DEMAND
with tabs[2]:
    def explorer(dim, label, ok):
        st.markdown(f'<div class="sec">All {label} (complete — search any value)</div>', unsafe_allow_html=True)
        find = st.text_input(f"Search {label}", key=f"s_{dim}", placeholder=f"type any {label[:-1]}…")
        w2, p2 = f"{W} AND {ok}", list(p)
        if find:
            w2 += f" AND {dim} ILIKE ?"; p2 += [f"%{find}%"]
        total = one(f"SELECT count(DISTINCT {dim}) FROM jobs WHERE {w2}", p2)[0]
        df = run(f"""SELECT {dim} AS "{label[:-1]}", count(*) postings,
                     count(DISTINCT company) employers,
                     count(salary_monthly_min) with_pay,
                     round(median(salary_monthly_min)) median_monthly
                     FROM jobs WHERE {w2} GROUP BY 1 ORDER BY postings DESC LIMIT 500""", p2)
        df["median_monthly"] = df["median_monthly"].map(inr)
        st.caption(f"{total:,} distinct {label} match — top 500 by postings (search to reach any one).")
        st.dataframe(df, use_container_width=True, hide_index=True)

    sub = st.radio("Dimension", ["Roles", "Industries", "Skills", "Work type"], horizontal=True)
    if sub == "Roles":
        explorer("role", "roles", ROLE_OK)
    elif sub == "Industries":
        st.markdown('<div class="note">Industry is provided by WorkIndia (100%), Foundit (95%) and '
                    'Jobhai (32%); apna/ncs/quikr do not supply it, so this view covers ~51% of postings.</div>',
                    unsafe_allow_html=True)
        explorer("industry", "industries", "industry IS NOT NULL AND industry<>''")
    elif sub == "Skills":
        st.markdown('<div class="note">Skills are free-text and present on ~38% of postings '
                    '(ncs/foundit/workindia strongest). Shown as provided, exact counts.</div>', unsafe_allow_html=True)
        explorer("skills", "skills", "skills IS NOT NULL AND skills<>''")
    else:
        df = run(f"""SELECT coalesce(employment_type_norm,'(unspecified)') AS "work type", count(*) postings
                     FROM jobs WHERE {W} GROUP BY 1 ORDER BY postings DESC LIMIT 12""", p)
        st.dataframe(df, use_container_width=True, hide_index=True)
        wfh = run(f"SELECT count(*) FILTER(WHERE is_wfh) w, count(*) n FROM jobs WHERE {W}", p).iloc[0]
        st.markdown(f'<div class="cap">Work-from-home flag set on {grp(wfh.w)} of {grp(wfh.n)} postings '
                    f'({100*int(wfh.w)/max(int(wfh.n),1):.1f}%). Only apna & jobhai reliably flag WFH, '
                    f'so this undercounts true remote roles.</div>', unsafe_allow_html=True)

# ================================================================ GEOGRAPHY
with tabs[3]:
    st.markdown('<div class="note">City & state are normalized from each board’s raw location '
                '(e.g. "Bengaluru/Bangalore", "Bengaluru, India", "Whitefield, Bangalore" → '
                '<b>Bengaluru, Karnataka</b>). Raw location is retained in the job records tab.</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        df = run(f"""SELECT city, any_value(state) AS "state", count(*) postings,
                     count(DISTINCT company) employers, round(median(salary_monthly_min)) median_monthly
                     FROM jobs WHERE {W} AND {CITY_OK} GROUP BY 1 ORDER BY postings DESC LIMIT 400""", p)
        df["median_monthly"] = df["median_monthly"].map(inr)
        tot = one(f"SELECT count(DISTINCT city) FROM jobs WHERE {W} AND {CITY_OK}", p)[0]
        st.markdown('<div class="sec">Cities</div>', unsafe_allow_html=True)
        st.caption(f"{tot:,} normalized cities — top 400 by postings.")
        st.dataframe(df, use_container_width=True, hide_index=True, height=440)
    with c2:
        dfs = run(f"""SELECT state AS "state", count(*) postings, count(DISTINCT city) FILTER(WHERE {CITY_OK}) cities
                      FROM jobs WHERE {W} AND state<>'(unknown)' GROUP BY 1 ORDER BY postings DESC""", p)
        st.markdown('<div class="sec">States</div>', unsafe_allow_html=True)
        st.caption(f"{len(dfs)} states · covers {int(k.states)} with known geography.")
        st.dataframe(dfs, use_container_width=True, hide_index=True, height=440)

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
    per = "posted_on::date" if g == "Daily" else f"date_trunc('{'week' if g == 'Weekly' else 'month'}', posted_on)::date"
    label = "day" if g == "Daily" else ("week" if g == "Weekly" else "month")
    st.markdown('<div class="note">Job postings counted by their <b>posting date</b> (the real post date '
                'from each source), newest first. The latest period is partial (still in progress), so it '
                'reads low. <b>change</b> = vs. the previous period.</div>', unsafe_allow_html=True)
    if g == "Daily":
        df = run(f"SELECT {per} AS date, dayname(posted_on) AS weekday, count(*) postings "
                 f"FROM jobs WHERE {Wt} GROUP BY 1,2 ORDER BY 1", pt)
        key_col = "date"
    else:
        df = run(f"SELECT {per} AS period, count(*) postings FROM jobs WHERE {Wt} GROUP BY 1 ORDER BY 1", pt)
        key_col = "period"
    if len(df):
        df["change"] = df["postings"].pct_change().map(lambda v: f"{v*100:+.0f}%" if pd.notna(v) else "—")
        df = df.iloc[::-1].reset_index(drop=True)
        st.markdown(f'<div class="sec">Postings per {label} · {win}</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True, height=460)
    if not B["key"]:
        st.markdown(f'<div class="sec">Postings per {label} by source</div>', unsafe_allow_html=True)
        dfb = run(f"SELECT {per} AS {key_col}, board, count(*) n FROM jobs WHERE {Wt} GROUP BY 1,2", pt)
        if len(dfb):
            piv = dfb.pivot(index=key_col, columns="board", values="n").fillna(0).astype(int)
            piv = piv.sort_index(ascending=False).reset_index()
            st.dataframe(piv, use_container_width=True, hide_index=True, height=460)

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
    df["median_monthly"] = df["median_monthly"].map(inr)
    st.caption(f"{total:,} distinct named employers match — top 500 by postings.")
    st.dataframe(df, use_container_width=True, hide_index=True, height=520)

# ================================================================ DATA & METHODOLOGY
with tabs[6]:
    st.markdown('<div class="sec">Record counts & field coverage by source</div>', unsafe_allow_html=True)
    st.markdown('<div class="cap">Every percentage is a live count over the current filter. This is the '
                'full picture of what is and isn’t captured — nothing is hidden.</div>', unsafe_allow_html=True)
    cov = run(f"""SELECT board,
      count(*) postings,
      round(100.0*count(*) FILTER(WHERE title IS NOT NULL AND title<>'')/count(*)) AS "title",
      round(100.0*count(*) FILTER(WHERE {CITY_OK})/count(*)) AS "city",
      round(100.0*count(*) FILTER(WHERE state<>'(unknown)')/count(*)) AS "state",
      round(100.0*count(*) FILTER(WHERE {ROLE_OK})/count(*)) AS "role",
      round(100.0*count(*) FILTER(WHERE industry IS NOT NULL AND industry<>'')/count(*)) AS "industry",
      round(100.0*count(salary_monthly_min)/count(*)) AS "pay",
      round(100.0*count(exp_years)/count(*)) AS "experience",
      round(100.0*count(*) FILTER(WHERE skills IS NOT NULL AND skills<>'')/count(*)) AS "skills",
      round(100.0*count(*) FILTER(WHERE posted_on IS NOT NULL)/count(*)) AS "posted"
      FROM jobs WHERE {W} GROUP BY 1 ORDER BY postings DESC""", p)
    for cc in ["title", "city", "state", "role", "industry", "pay", "experience", "skills", "posted"]:
        cov[cc] = cov[cc].map(lambda v: f"{int(v)}%" if pd.notna(v) else "—")
    st.dataframe(cov, use_container_width=True, hide_index=True)
    st.markdown("""<div class="note" style="margin-top:14px;">
      <b>Methodology.</b><br>
      • <b>Sources</b>: apna.co, workindia.in, jobhai.com, ncs.gov.in, foundit.in, quikr.com — public
      listings only. <b>De-duplication</b>: by each source’s native job id; a job is counted once.<br>
      • <b>Posting date</b>: the real date from each source (apna created_on, workindia created_at,
      jobhai URL epoch, ncs page date, foundit datePosted, quikr JSON-LD datePosted), standardized to IST.<br>
      • <b>Geography</b>: raw location → canonical city + state via an alias/locality map; raw kept.<br>
      • <b>Pay</b>: normalized to monthly ₹ (foundit/ncs annual ÷12); 0 = not disclosed; clipped to
      ₹1k–₹50L/month. Disclosure rates vary by source (see "pay" column) and are shown, never hidden.<br>
      • <b>Not inflated</b>: ranked lists drop "(not specified)"/placeholder buckets but totals keep them;
      "distinct roles/companies" are raw source values, not merged.<br>
      • <b>Read-only</b>: this dashboard only reads a data snapshot; it never writes to the database.
    </div>""", unsafe_allow_html=True)

# ================================================================ JOB RECORDS
with tabs[7]:
    st.caption(f"{grp(k.jobs)} postings match. Showing the 1,000 most recent; download the full "
               f"filtered set below. Each row links to the live posting.")
    rows = run(f"""SELECT board, title, company, city, state, role, industry,
                   salary_monthly_min, salary_monthly_max, experience, employment_type_norm AS work_type,
                   is_wfh, posted_on, url
                   FROM jobs WHERE {W} ORDER BY posted_on DESC NULLS LAST LIMIT 1000""", p)
    st.dataframe(rows, use_container_width=True, hide_index=True, height=560, column_config={
        "url": st.column_config.LinkColumn("link", display_text="open ↗"),
        "posted_on": st.column_config.DatetimeColumn("posted", format="YYYY-MM-DD"),
        "salary_monthly_min": st.column_config.NumberColumn("pay min/mo", format="₹%d"),
        "salary_monthly_max": st.column_config.NumberColumn("pay max/mo", format="₹%d")})
    # build the full CSV only on demand (keeps memory flat; 900k+ rows aren't materialized on every view)
    if st.checkbox(f"Prepare download of all {grp(k.jobs)} filtered records"):
        full = con().execute(f"""SELECT board, job_id, title, company, city, state, location, role, industry,
                   salary_min, salary_max, salary_monthly_min, salary_monthly_max, experience, exp_years,
                   employment_type, employment_type_norm, education, skills, is_wfh, posted_on, url
                   FROM jobs WHERE {W} ORDER BY posted_on DESC NULLS LAST""", p).df()
        st.download_button(f"⬇ Download CSV ({grp(len(full))} rows)",
                           full.to_csv(index=False).encode("utf-8"),
                           file_name=f"{(B['key'] or 'all')}_talent_demand.csv", mime="text/csv")
