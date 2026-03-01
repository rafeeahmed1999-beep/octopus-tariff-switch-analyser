import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import io
from datetime import datetime, timedelta

st.set_page_config(page_title="Octopus Tariff Switch Analyser", layout="wide")

C = {
    'primary':   '#FF1F5A',
    'secondary': '#5C2D91',
    'accent':    '#00B4D8',
    'positive':  '#06D6A0',
    'warning':   '#FFB703',
    'neutral':   '#ADB5BD',
    'bg':        '#0F0F1A',
    'surface':   '#1A1A2E',
    'text':      '#E8E8F0',
}

BL = dict(
    template='plotly_dark',
    paper_bgcolor=C['bg'],
    plot_bgcolor=C['surface'],
    font=dict(family='Inter, Arial, sans-serif', color='#FFFFFF', size=13),
    margin=dict(l=50, r=30, t=60, b=40),
)

def chart_title(text):
    return dict(text=text, font=dict(color='#FFFFFF', size=14))

st.markdown("""
<style>
.stApp { background-color: #0F0F1A; color: #E8E8F0; }
.metric-card {
    background: #1A1A2E; border: 1px solid #5C2D91;
    border-radius: 8px; padding: 16px 20px; text-align: center; margin-bottom: 8px;
}
.metric-card h3 { color: #ADB5BD; font-size: 12px; margin: 0 0 6px 0;
    text-transform: uppercase; letter-spacing: 0.05em; }
.metric-card p { color: #E8E8F0; font-size: 24px; font-weight: 700; margin: 0; }
.metric-card span { color: #06D6A0; font-size: 12px; }
.info-box {
    background: #1A1A2E; border-left: 3px solid #00B4D8;
    border-radius: 4px; padding: 14px 18px; margin-bottom: 10px;
}
.info-box h4 { color: #00B4D8; margin: 0 0 6px 0; font-size: 14px; }
.info-box p  { color: #ADB5BD; margin: 0; font-size: 13px; line-height: 1.5; }
.profile-box {
    background: #1A1A2E; border: 1px solid #06D6A0;
    border-radius: 8px; padding: 20px 24px; margin-top: 16px;
}
.profile-box h4 { color: #06D6A0; margin: 0 0 10px 0; font-size: 15px; }
.profile-box p  { color: #E8E8F0; margin: 0 0 8px 0; font-size: 13px; line-height: 1.6; }
.profile-box ul { color: #ADB5BD; font-size: 13px; line-height: 1.8; padding-left: 18px; margin: 0; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# AGILE PRICES  --  real data from Octopus public API
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_agile_prices(days_back: int, region: str):
    """
    Fetches real Agile Octopus half-hourly unit rates (p/kWh inc. VAT)
    from the Octopus public API. No API key required.

    Both arguments are part of the cache key, so changing region or date
    range triggers a fresh API call rather than returning a stale result.

    Falls back to a synthetic price curve if the API is unreachable.
    """
    period_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00Z")
    period_to   = datetime.utcnow().strftime("%Y-%m-%dT23:30Z")
    product     = "AGILE-24-10-01"
    tariff      = f"E-1R-{product}-{region}"
    url = (
        f"https://api.octopus.energy/v1/products/{product}"
        f"/electricity-tariffs/{tariff}/standard-unit-rates/"
        f"?period_from={period_from}&period_to={period_to}&page_size=25000"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results:
            return _fallback_prices(days_back), True
        df = pd.DataFrame(results)
        df["valid_from"]  = pd.to_datetime(df["valid_from"], utc=True)
        df                = df.sort_values("valid_from").reset_index(drop=True)
        df["hour"]        = df["valid_from"].dt.hour + df["valid_from"].dt.minute / 60
        df["price_p_kwh"] = df["value_inc_vat"]
        return df[["valid_from", "hour", "price_p_kwh"]], False
    except Exception:
        return _fallback_prices(days_back), True


def _fallback_prices(days_back):
    np.random.seed(42)
    n   = days_back * 48
    idx = pd.date_range(datetime.utcnow() - timedelta(days=days_back),
                        periods=n, freq="30min", tz="UTC")
    h = idx.hour + idx.minute / 60
    p = np.maximum(
        18 + 8 * np.sin(np.pi * (h - 6) / 12)
           + 15 * np.exp(-0.5 * ((h - 17.5) / 1.5) ** 2)
           + np.random.normal(0, 3, n),
        1.0,
    )
    return pd.DataFrame({"valid_from": idx, "hour": h, "price_p_kwh": p})


def build_price_profile(agile_df):
    df = agile_df.copy()
    df["slot"] = (df["hour"] * 2).astype(int) / 2
    return df.groupby("slot")["price_p_kwh"].mean().reset_index().rename(columns={"slot": "hour"})


# ══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC CUSTOMER COHORT
# ══════════════════════════════════════════════════════════════════════════════

def generate_customers(n, agile_peak_p, agile_offpk_p, agile_avg_p, seed=42):
    """
    Generates a synthetic cohort of UK energy customers.

    -- What is real vs synthetic --
    REAL (from Octopus API):
      agile_peak_p  -- average Agile rate during 16:00-19:00 (p/kWh)
      agile_offpk_p -- average Agile rate outside 16:00-19:00 (p/kWh)
      agile_avg_p   -- overall average Agile rate across all half-hour slots (p/kWh)

    SYNTHETIC (researched and derived by author):
      Everything else. Numbers are calibrated to produce realistic annual kWh
      figures (2,500-4,500 kWh/yr) and plausible cost differences between
      tariffs, using domain knowledge of UK household energy use and retail
      energy pricing structures.

    -- Consumption model --
    Each customer has a base kWh per half-hour slot.
    Their actual usage per slot is scaled by two multipliers:

      pm (peak multiplier):
        How much more or less than base they use during the 6 peak slots (16-19h).
        pm > 1 means heavy peak usage. pm < 1 means they actively avoid the peak.
        Example: Peak Heavy has pm=3.50 -- they use 3.5x base during peak hours.

      om (off-peak multiplier):
        How much more or less than base they use across the 42 off-peak slots.
        Example: Off-Peak Opportunist has om=1.10 -- slightly above base off-peak,
        reflecting load-shifting (e.g. running dishwasher at midnight) but NOT
        higher total consumption. Their base is lower to compensate.

    Annual kWh = (6 peak slots x pu + 42 off-peak slots x ou) x 365 days
    where pu = base x pm, ou = base x om.

    -- Segment calibration --
    Segment bases are set so all four segments produce comparable annual kWh.
    Off-Peak Opportunist has a LOWER base than other segments.
    They don't use more electricity -- they use it smarter.

    -- Tariff cost model --
    Standard: flat rate drawn from U(24, 26) p/kWh -- UK Oct 2024 price cap level.

    Agile (blended): peak_frac x agile_peak_p + (1 - peak_frac) x agile_offpk_p
      Uses real API prices. Peak Heavy pays close to agile_peak_p (~35-50p).
      Off-Peak Opportunist pays close to agile_offpk_p (~10-18p).

    Tracker: agile_avg_p x U(1.15, 1.25)
      Tracker follows the daily wholesale average but includes a supplier margin.
      The 15-25% uplift reflects hedging costs and admin -- a reasonable estimate
      based on domain knowledge of retail energy pricing.
      This makes Tracker more expensive than Agile for flexible users but cheaper
      than Standard for stable users who benefit from wholesale dips without
      needing to time-shift.
    """
    np.random.seed(seed)

    # w    = population weight (must sum to 1.0)
    # base = kWh per half-hour slot before multipliers applied
    # pm   = peak multiplier (applied to 6 slots: 16:00-19:00)
    # om   = off-peak multiplier (applied to 42 remaining slots)
    segs = {
        "Low & Stable":         {"w": 0.25, "base": 0.20, "pm": 1.15, "om": 0.97},
        "High & Stable":        {"w": 0.30, "base": 0.45, "pm": 1.20, "om": 0.97},
        "Peak Heavy":           {"w": 0.28, "base": 0.28, "pm": 3.50, "om": 0.30},
        "Off-Peak Opportunist": {"w": 0.17, "base": 0.18, "pm": 0.25, "om": 1.10},
    }

    chosen = np.random.choice(list(segs), size=n, p=[v["w"] for v in segs.values()])

    vol_ranges = {
        "Low & Stable":         (0.30, 0.50),
        "High & Stable":        (0.40, 0.60),
        "Peak Heavy":           (0.65, 0.90),
        "Off-Peak Opportunist": (0.10, 0.35),
    }

    rows = []
    for seg in chosen:
        s    = segs[seg]
        base = s["base"] * np.random.uniform(0.85, 1.15)

        pu = base * s["pm"] * np.random.uniform(0.9, 1.1)
        ou = base * s["om"] * np.random.uniform(0.9, 1.1)

        annual_kwh = (6 * pu + 42 * ou) * 365
        peak_frac  = (6 * pu) / (6 * pu + 42 * ou)

        std_rate      = np.random.uniform(24.0, 26.0)
        agile_blended = peak_frac * agile_peak_p + (1 - peak_frac) * agile_offpk_p
        tracker_rate  = agile_avg_p * np.random.uniform(1.15, 1.25)

        cost_std = annual_kwh * std_rate      / 100
        cost_agl = annual_kwh * agile_blended / 100
        cost_trk = annual_kwh * tracker_rate  / 100

        best   = min(
            [("Standard", cost_std), ("Agile", cost_agl), ("Tracker", cost_trk)],
            key=lambda x: x[1],
        )[0]
        saving = cost_std - min(cost_std, cost_agl, cost_trk)

        lo, hi = vol_ranges[seg]
        rows.append({
            "segment":             seg,
            "annual_kwh":          round(annual_kwh, 1),
            "peak_fraction":       round(peak_frac, 3),
            "current_tariff":      "Standard",
            "recommended_tariff":  best,
            "cost_standard":       round(cost_std, 2),
            "cost_agile":          round(cost_agl, 2),
            "cost_tracker":        round(cost_trk, 2),
            "annual_saving":       round(max(saving, 0), 2),
            "volatility_exposure": round(np.random.uniform(lo, hi), 3),
        })

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## Controls")
    st.markdown("---")

    regions = {
        "London (C)":     "C",
        "SE England (J)": "J",
        "E.England (A)":  "A",
        "W.Midlands (E)": "E",
        "NW England (G)": "G",
        "Yorkshire (M)":  "M",
        "SW England (N)": "N",
    }
    region_label = st.selectbox("Agile region", list(regions))
    region_code  = regions[region_label]
    days_back    = st.slider("Price history (days)", 14, 90, 60)
    n_customers  = st.slider("Cohort size", 200, 2000, 1000, step=100)
    seg_filter   = st.multiselect(
        "Customer segments",
        ["Low & Stable", "High & Stable", "Peak Heavy", "Off-Peak Opportunist"],
        default=["Low & Stable", "High & Stable", "Peak Heavy", "Off-Peak Opportunist"],
    )
    min_saving = st.slider("Min saving to recommend switch (£/yr)", 0, 200, 100, step=10)

    st.markdown("---")
    st.markdown(
        "Agile prices fetched live from the "
        "[Octopus public API](https://developer.octopus.energy/rest/reference). "
        "Customer behaviour data is synthetic -- see README for methodology."
    )


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

with st.spinner("Fetching Agile prices from Octopus API..."):
    agile_df, is_fallback = fetch_agile_prices(days_back, region_code)

prof    = build_price_profile(agile_df)
peak_p  = float(prof.loc[prof["hour"].between(16, 18.5),  "price_p_kwh"].mean())
offpk_p = float(prof.loc[~prof["hour"].between(16, 18.5), "price_p_kwh"].mean())
avg_p   = float(prof["price_p_kwh"].mean())

df_all = generate_customers(n_customers, peak_p, offpk_p, avg_p)
df     = df_all[df_all["segment"].isin(seg_filter)].copy()

df["switch_recommended"] = (
    (df["recommended_tariff"] != "Standard") & (df["annual_saving"] >= min_saving)
)
df["display_tariff"] = np.where(df["switch_recommended"], df["recommended_tariff"], "Standard")

pal       = [C["accent"], C["warning"], C["primary"], C["positive"]]
color_map = dict(zip(
    ["Low & Stable", "High & Stable", "Peak Heavy", "Off-Peak Opportunist"], pal
))


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# Octopus Energy -- Customer Tariff Switch Analyser")
st.markdown(
    "A simulation of how Octopus Energy might identify which customers would benefit "
    "from switching to a variable tariff, and which are already on the right deal."
)

if is_fallback:
    st.warning("Could not reach the Octopus API -- showing synthetic fallback prices.")

sw    = df[df["switch_recommended"]]
stay  = df[~df["switch_recommended"]]
pct   = len(sw) / len(df) * 100 if len(df) else 0
avg_s = sw["annual_saving"].mean() if len(sw) else 0


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "Segment Overview",
    "Savings Estimator",
    "Usage vs Price Volatility",
    "Customer Report",
])


# ── Tab 1 ─────────────────────────────────────────────────────────────────────
with tab1:

    # Tariff explainers
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        st.markdown("""
        <div class="info-box">
            <h4>Standard Tariff</h4>
            <p>A fixed unit rate (~24-26p/kWh) regardless of when you use power.
            Predictable bills but no opportunity to benefit from cheaper off-peak electricity.
            The most common tariff in the UK.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_e2:
        st.markdown(f"""
        <div class="info-box">
            <h4>Agile Octopus</h4>
            <p>Half-hourly prices that follow the wholesale electricity market.
            Cheap overnight (sometimes negative), expensive during the 4-7pm evening peak.
            Rewards customers who can shift flexible loads away from peak hours.
            Current avg: <b>{avg_p:.1f}p/kWh</b> in {region_label}.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_e3:
        st.markdown("""
        <div class="info-box">
            <h4>Tracker Tariff</h4>
            <p>A daily rate that tracks the wholesale market plus a supplier margin.
            Less volatile than Agile, changing once per day rather than every 30 minutes.
            A middle ground for customers who want some wholesale benefit without
            actively managing when they use power.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    **What this tool shows:** Not every customer benefits from switching to a variable tariff.
    A Peak Heavy customer who uses most of their electricity during the expensive 4-7pm window
    will likely pay more on Agile than on Standard. This tool segments a synthetic customer
    cohort by usage behaviour to identify who should switch, who should stay, and what the
    expected saving is for each group. Agile prices are fetched live from the Octopus public
    API -- change the region in the sidebar to see how recommendations shift by geography.
    """)

    st.markdown("---")

    # Metrics tiles
    for col, title, val, sub in zip(
        st.columns(5),
        ["Customers analysed", "Should switch", "Should stay on Standard",
         "Avg annual saving", "Avg Agile rate"],
        [f"{len(df):,}", f"{len(sw):,}", f"{len(stay):,}",
         f"£{avg_s:.0f}", f"{avg_p:.1f}p/kWh"],
        [f"{len(seg_filter)} segment(s)", f"{pct:.1f}% of cohort",
         f"{100 - pct:.1f}% of cohort", "per switching customer",
         f"last {days_back} days, {region_label}"],
    ):
        with col:
            st.markdown(
                f'<div class="metric-card"><h3>{title}</h3><p>{val}</p><span>{sub}</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Customer Segment Breakdown")
    st.caption(
        "Each segment represents a UK energy customer archetype. "
        "Recommended tariff is driven by when customers use power relative to Agile's price curve. "
        "The min saving threshold set in the sidebar is applied throughout."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        counts = df["segment"].value_counts().reset_index()
        counts.columns = ["segment", "count"]
        fig = go.Figure(go.Pie(
            labels=counts["segment"], values=counts["count"], hole=0.55,
            marker_colors=pal, textinfo="label+percent",
            textfont=dict(size=12, color="white"),
            hovertemplate="%{label}<br>%{value:,} customers (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            **BL,
            title=chart_title("Cohort Composition"),
            height=380, showlegend=False,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#FFFFFF")),
            annotations=[dict(text=f"{len(df):,}<br>customers", x=0.5, y=0.5,
                               font=dict(size=14, color="white"), showarrow=False)],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        rec = df.groupby(["segment", "display_tariff"]).size().reset_index(name="count")
        fig = go.Figure()
        for tariff, color in [
            ("Standard", C["neutral"]), ("Agile", C["accent"]), ("Tracker", C["positive"])
        ]:
            sub = rec[rec["display_tariff"] == tariff]
            fig.add_trace(go.Bar(
                x=sub["segment"], y=sub["count"], name=tariff, marker_color=color,
                hovertemplate=f"%{{x}}<br>%{{y}} customers -> {tariff}<extra></extra>",
            ))
        fig.update_layout(
            **BL,
            title=chart_title(f"Recommended Tariff by Segment (min saving >= £{min_saving}/yr)"),
            barmode="stack", height=380, xaxis_title="", yaxis_title="Customers",
            legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#FFFFFF")),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Segment Summary")
    summary = df.groupby("segment").agg(
        customers   =("segment", "count"),
        avg_kwh     =("annual_kwh", "mean"),
        pct_agile   =("display_tariff", lambda x: (x == "Agile").mean() * 100),
        pct_tracker =("display_tariff", lambda x: (x == "Tracker").mean() * 100),
        pct_standard=("display_tariff", lambda x: (x == "Standard").mean() * 100),
        avg_saving  =("annual_saving", lambda x: x[df.loc[x.index, "switch_recommended"]].mean()),
    ).round(1).reset_index()
    summary.columns = [
        "Segment", "Customers", "Avg kWh/yr",
        "% to Agile", "% to Tracker", "% stay Standard", "Avg Saving (£)"
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### Who is Agile ideal for?")

    agile_cust       = df[df["display_tariff"] == "Agile"]
    agile_avg_saving = agile_cust["annual_saving"].mean() if len(agile_cust) else 0
    agile_avg_kwh    = agile_cust["annual_kwh"].mean() if len(agile_cust) else 0
    agile_peak_pct   = agile_cust["peak_fraction"].mean() * 100 if len(agile_cust) else 0
    dominant_seg     = agile_cust["segment"].value_counts().idxmax() if len(agile_cust) else "Off-Peak Opportunist"

    st.markdown(f"""
    <div class="profile-box">
        <h4>The Ideal Agile Customer -- derived from this cohort</h4>
        <p>
        The strongest Agile candidates in this cohort are concentrated in the
        <b>{dominant_seg}</b> segment. The profile below is calculated directly
        from the current data and updates when you change region or cohort size.
        </p>
        <ul>
            <li><b>Usage pattern:</b> Only ~{agile_peak_pct:.0f}% of their daily
            consumption falls in peak hours (16:00-19:00). The majority of their
            usage sits in overnight or daytime off-peak slots where Agile rates
            average {offpk_p:.1f}p/kWh.</li>
            <li><b>Typical consumption:</b> Around {agile_avg_kwh:,.0f} kWh/year.
            They are not necessarily low consumers -- they are smart schedulers.</li>
            <li><b>Lifestyle indicators:</b> Works from home or keeps flexible hours;
            charges an EV overnight; runs dishwasher and washing machine on a timer
            after midnight; comfortable checking the Agile app before running
            high-draw appliances.</li>
            <li><b>Financial outcome:</b> Projected saving of
            <b>£{agile_avg_saving:.0f}/year</b> vs Standard, driven by accessing
            off-peak Agile slots at {offpk_p:.1f}p/kWh vs a Standard flat rate
            of ~25p/kWh.</li>
            <li><b>Why Agile beats Tracker for this group:</b> Tracker adds a
            supplier margin on top of the wholesale daily average. Customers who
            actively time-shift their usage can beat that average by targeting
            the cheapest individual slots -- something Tracker's single daily
            rate does not reward.</li>
        </ul>
        <p style="margin-top:10px; color:#ADB5BD;">
        <i>By contrast, a Peak Heavy customer faces Agile rates of {peak_p:.1f}p/kWh
        during their peak usage hours. For them, a Standard flat rate of ~25p/kWh
        is the financially rational choice -- and this tool correctly flags them
        to stay put.</i>
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Tab 2 ─────────────────────────────────────────────────────────────────────
with tab2:
    st.subheader("Annual Savings by Switching Tariff")
    st.caption(
        "Savings estimated against remaining on Standard. "
        "The saving distribution only shows customers recommended to switch. "
        "The cost chart shows all customers so volume differences between segments are visible."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        fig = go.Figure()
        for seg, color in color_map.items():
            sub = df[(df["segment"] == seg) & df["switch_recommended"]]["annual_saving"]
            if len(sub) == 0:
                continue
            fig.add_trace(go.Box(
                y=sub, name=seg, marker_color=color, line_color=color,
                boxmean=True, hovertemplate="%{y:.0f} £/yr<extra></extra>",
            ))
        fig.update_layout(
            **BL,
            title=chart_title("Saving Distribution -- Switch Candidates Only (£/yr)"),
            height=420, yaxis_title="Annual Saving (£)", showlegend=False,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#FFFFFF")),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        costs = df.groupby("segment")[
            ["cost_standard", "cost_agile", "cost_tracker"]
        ].mean().round(0)
        fig = go.Figure()
        for col_name, label, color in [
            ("cost_standard", "Standard", C["neutral"]),
            ("cost_agile",    "Agile",    C["accent"]),
            ("cost_tracker",  "Tracker",  C["positive"]),
        ]:
            fig.add_trace(go.Bar(
                name=label, x=costs.index.tolist(), y=costs[col_name], marker_color=color,
                hovertemplate=f"{label}: £%{{y:,.0f}}<extra></extra>",
            ))
        fig.update_layout(
            **BL,
            title=chart_title("Average Annual Cost by Tariff and Segment (£)"),
            barmode="group", height=420, yaxis_title="Annual Cost (£)",
            legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#FFFFFF")),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Switch Recommendation Breakdown")
    rs = (
        df.groupby(["segment", "display_tariff"])
        .agg(customers=("segment", "count"), avg_saving=("annual_saving", "mean"))
        .round(1).reset_index()
    )
    rs.columns = ["Segment", "Recommended Tariff", "Customers", "Avg Saving (£)"]
    st.dataframe(rs, use_container_width=True, hide_index=True)


# ── Tab 3 ─────────────────────────────────────────────────────────────────────
with tab3:
    st.subheader("Usage Profile vs Price Volatility Exposure")
    st.caption(
        "Peak Heavy customers have high volatility exposure but Agile costs them more, not less -- "
        "their usage coincides with the most expensive slots. "
        "Off-Peak Opportunists have low exposure and the highest savings."
    )

    col_a, col_b = st.columns([3, 2])

    with col_a:
        fig = go.Figure()
        for seg, color in color_map.items():
            sub = df[df["segment"] == seg]
            if len(sub) == 0:
                continue
            fig.add_trace(go.Scatter(
                x=sub["volatility_exposure"], y=sub["annual_saving"],
                mode="markers", name=seg,
                marker=dict(color=color, size=5, opacity=0.55),
                hovertemplate=(
                    f"<b>{seg}</b><br>"
                    "Exposure: %{x:.2f}<br>Saving: £%{y:.0f}<extra></extra>"
                ),
            ))
        fig.add_vline(
            x=0.5, line=dict(color=C["neutral"], width=1, dash="dash"),
            annotation_text="High vol. threshold",
            annotation_font_color="#FFFFFF",
        )
        fig.add_hline(
            y=min_saving, line=dict(color=C["warning"], width=1, dash="dot"),
            annotation_text=f"Min saving threshold £{min_saving}",
            annotation_font_color="#FFB703",
        )
        fig.update_layout(
            **BL,
            title=chart_title("Volatility Exposure vs Potential Annual Saving"),
            height=440, xaxis_title="Volatility Exposure Score (0-1)",
            yaxis_title="Annual Saving vs Standard (£)",
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#FFFFFF")),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prof["hour"], y=prof["price_p_kwh"],
            mode="lines", fill="tozeroy",
            fillcolor="rgba(255,31,90,0.12)",
            line=dict(color=C["primary"], width=2),
            hovertemplate="%{x:.1f}h -- %{y:.1f}p/kWh<extra></extra>",
        ))
        fig.add_vrect(
            x0=16, x1=19, fillcolor="rgba(255,31,90,0.15)", line_width=0,
            annotation_text="Evening peak", annotation_font_color="#FF1F5A",
            annotation_position="top left",
        )
        fig.add_vrect(
            x0=0, x1=7, fillcolor="rgba(6,214,160,0.10)", line_width=0,
            annotation_text="Cheap overnight", annotation_font_color="#06D6A0",
            annotation_position="top right",
        )
        fig.update_layout(
            **BL,
            title=chart_title(f"Real Agile Profile -- {region_label}"),
            height=440, xaxis_title="Hour of day", yaxis_title="Avg price (p/kWh)",
            showlegend=False, legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Peak vs Off-Peak Usage Share by Segment")
    pp = df.groupby("segment")["peak_fraction"].mean().reset_index()
    pp["offpeak"] = 1 - pp["peak_fraction"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pp["segment"], y=pp["peak_fraction"] * 100,
        name="Peak (16:00-19:00)", marker_color=C["primary"],
    ))
    fig.add_trace(go.Bar(
        x=pp["segment"], y=pp["offpeak"] * 100,
        name="Off-peak", marker_color=C["positive"],
    ))
    fig.update_layout(
        **BL,
        title=chart_title("Peak vs Off-Peak Usage Share by Segment"),
        barmode="stack", height=300, yaxis_title="% of daily usage",
        legend=dict(orientation="h", y=1.12, bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#FFFFFF")),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Tab 4 ─────────────────────────────────────────────────────────────────────
with tab4:
    st.subheader("Switch Recommendation Report")
    st.caption(
        "Full cohort breakdown with recommended tariff and projected saving. "
        "Recommendations apply the min saving threshold set in the sidebar. "
        "Download as CSV for campaign planning."
    )

    report = df[[
        "segment", "annual_kwh", "current_tariff", "display_tariff",
        "cost_standard", "cost_agile", "cost_tracker",
        "annual_saving", "volatility_exposure", "switch_recommended",
    ]].copy()
    report.columns = [
        "Segment", "Annual kWh", "Current Tariff", "Recommended Tariff",
        "Cost Standard (£)", "Cost Agile (£)", "Cost Tracker (£)",
        "Annual Saving (£)", "Volatility Exposure", "Switch Recommended",
    ]

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        sw_only = st.checkbox("Show switch candidates only", value=False)
    with col_f2:
        tf = st.selectbox("Filter by recommended tariff",
                           ["All", "Standard", "Agile", "Tracker"])

    out = report.copy()
    if sw_only:
        out = out[out["Switch Recommended"]]
    if tf != "All":
        out = out[out["Recommended Tariff"] == tf]

    st.markdown(f"Showing **{len(out):,}** customers")
    st.dataframe(out.head(500), use_container_width=True, hide_index=True)

    buf = io.StringIO()
    out.to_csv(buf, index=False)
    st.download_button(
        "Download report (CSV)", buf.getvalue(),
        "tariff_switch_recommendations.csv", "text/csv",
    )

    st.markdown("---")
    st.markdown(
        f"**Data note:** Agile unit rates are fetched live from the "
        f"[Octopus Energy public API](https://developer.octopus.energy/rest/reference) "
        f"for the {region_label} region. "
        "Customer records are synthetic -- see README for full methodology."
    )
