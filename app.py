import io
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.data_loader import load_uploaded_file, generate_demo_data
from utils.analytics import build_summary, build_product_performance, previous_period_metrics, safe_date_range
from utils.insights import generate_insights

st.set_page_config(page_title="InsightDash | UrbanWear Sales Intelligence", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ---------------------------- Styling ----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
[data-testid="stAppViewContainer"] { background: #f6f8fb; }
[data-testid="stSidebar"] { background: #101827; }
[data-testid="stSidebar"] * { color: #e8edf5 !important; }
[data-testid="stSidebar"] .stRadio label { padding: 7px 0; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
.insightdash-brand { font-size: 1.35rem; font-weight: 700; letter-spacing: -.03em; margin-bottom: .25rem; }
.brand-mark { display:inline-flex; width:34px; height:34px; border-radius:10px; align-items:center; justify-content:center; background:#ffffff; color:#101827; margin-right:9px; font-weight:800; }
.eyebrow { color:#6b7280; font-size:.78rem; text-transform:uppercase; letter-spacing:.12em; font-weight:700; }
.page-title { font-size:2rem; font-weight:750; letter-spacing:-.04em; color:#111827; margin:0; }
.page-subtitle { color:#667085; margin-top:.3rem; }
.kpi { background:#fff; border:1px solid #e6eaf0; border-radius:16px; padding:18px 20px; box-shadow:0 3px 14px rgba(16,24,40,.04); min-height:116px; }
.kpi-label { color:#667085; font-size:.78rem; font-weight:600; }
.kpi-value { color:#111827; font-size:1.65rem; font-weight:750; margin-top:7px; }
.kpi-delta { font-size:.78rem; margin-top:6px; }
.section-card { background:#fff; border:1px solid #e6eaf0; border-radius:16px; padding:18px; box-shadow:0 3px 14px rgba(16,24,40,.035); }
.insight { background:#fff; border:1px solid #e6eaf0; border-left:4px solid #344054; border-radius:12px; padding:13px 15px; margin-bottom:9px; color:#344054; }
.small-muted { color:#667085; font-size:.82rem; }
[data-testid="stMetric"] { background:#fff; }
</style>
""", unsafe_allow_html=True)


def money(v):
    return f"${v:,.0f}"


def render_kpi(label, value, delta=None):
    delta_html = ""
    if delta is not None:
        cls = "" if delta >= 0 else ""
        delta_html = f'<div class="kpi-delta">{"↑" if delta >= 0 else "↓"} {abs(delta):.1f}% vs previous period</div>'
    st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div>{delta_html}</div>', unsafe_allow_html=True)


# ---------------------------- State ----------------------------
if "raw_df" not in st.session_state:
    st.session_state.raw_df = generate_demo_data(1200)
    st.session_state.source_name = "UrbanWear Demo"
    st.session_state.demo_mode = True
if "upload_warnings" not in st.session_state:
    st.session_state.upload_warnings = []

# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.markdown('<div class="insightdash-brand"><span class="brand-mark">ID</span>InsightDash</div>', unsafe_allow_html=True)
    st.caption("Sales intelligence for small businesses")
    st.divider()
    page = st.radio("Navigation", ["Dashboard", "Upload Data", "Analytics", "Settings"], label_visibility="collapsed")
    st.divider()
    st.markdown("**Filters**")

    raw = st.session_state.raw_df.copy()
    min_d, max_d = safe_date_range(raw)
    date_value = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
    if isinstance(date_value, tuple) and len(date_value) == 2:
        start_date, end_date = date_value
    else:
        start_date, end_date = min_d, max_d

    products = sorted(raw["Product"].dropna().astype(str).unique()) if "Product" in raw else []
    categories = sorted(raw["Category"].dropna().astype(str).unique()) if "Category" in raw else []
    product_filter = st.multiselect("Product", products, placeholder="All products")
    category_filter = st.multiselect("Category", categories, placeholder="All categories")
    channel_filter = []
    if "Sales Channel" in raw.columns:
        channel_filter = st.multiselect("Sales channel", sorted(raw["Sales Channel"].dropna().astype(str).unique()), placeholder="All channels")

    st.divider()
    mode_text = "DEMO MODE" if st.session_state.demo_mode else "LIVE DATA"
    st.markdown(f"**{mode_text}**")
    st.caption(st.session_state.source_name)

# ---------------------------- Filtered data ----------------------------
def apply_filters(df, start, end, products=None, categories=None, channels=None):
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out[(out["Date"].dt.date >= start) & (out["Date"].dt.date <= end)]
    if products:
        out = out[out["Product"].isin(products)]
    if categories:
        out = out[out["Category"].isin(categories)]
    if channels and "Sales Channel" in out:
        out = out[out["Sales Channel"].isin(channels)]
    return out


df = apply_filters(raw, start_date, end_date, product_filter, category_filter, channel_filter)

# Previous period uses identical non-date filters.
period_days = max(1, (end_date - start_date).days + 1)
prev_end = start_date - timedelta(days=1)
prev_start = prev_end - timedelta(days=period_days - 1)
prev_df = apply_filters(raw, prev_start, prev_end, product_filter, category_filter, channel_filter)

summary = build_summary(df)
prev_summary = build_summary(prev_df)
deltas = previous_period_metrics(summary, prev_summary)

# ---------------------------- Upload page ----------------------------
if page == "Upload Data":
    st.markdown('<div class="eyebrow">Data workspace</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Upload Your Data</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Drop in a CSV or Excel export. InsightDash detects common columns, cleans safe issues, and rebuilds the dashboard automatically.</p>', unsafe_allow_html=True)
    st.write("")
    uploaded = st.file_uploader("Choose a CSV or XLSX file", type=["csv", "xlsx"], help="Your file is processed in memory for this MVP; no database is required.")
    if uploaded is not None:
        if st.button("Analyze File", type="primary", use_container_width=False):
            with st.spinner("Reading and validating your sales data..."):
                result = load_uploaded_file(uploaded)
            if result["error"]:
                st.error(result["error"])
            else:
                st.session_state.raw_df = result["data"]
                st.session_state.source_name = uploaded.name
                st.session_state.demo_mode = False
                st.session_state.upload_warnings = result["warnings"]
                st.success(f"Loaded {len(result['data']):,} transactions from {uploaded.name}.")
                st.rerun()

    st.markdown("### Data validation")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(raw):,}")
    c2.metric("Date range", f"{min_d:%d %b %Y} → {max_d:%d %b %Y}")
    c3.metric("Columns detected", f"{len(raw.columns)}")
    if st.session_state.upload_warnings:
        st.warning("Some safe cleanup actions or warnings were detected.")
        for warning in st.session_state.upload_warnings:
            st.write(f"• {warning}")
    st.markdown("### Detected schema")
    st.dataframe(pd.DataFrame({"Column": raw.columns, "Type": [str(raw[c].dtype) for c in raw.columns]}), use_container_width=True, hide_index=True)
    st.markdown("### Preview")
    st.dataframe(raw.head(20), use_container_width=True, hide_index=True)

# ---------------------------- Settings ----------------------------
elif page == "Settings":
    st.markdown('<div class="eyebrow">Workspace</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Settings</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Lightweight controls for the MVP workspace.</p>', unsafe_allow_html=True)
    st.write("")
    st.toggle("Use compact chart labels", value=False, disabled=True)
    st.info("InsightDash is intentionally database-free in this MVP. Uploaded files live in the current Streamlit session.")
    if st.button("Reset to UrbanWear demo", type="secondary"):
        st.session_state.raw_df = generate_demo_data(1200)
        st.session_state.source_name = "UrbanWear Demo"
        st.session_state.demo_mode = True
        st.session_state.upload_warnings = []
        st.rerun()

# ---------------------------- Analytics page ----------------------------
elif page == "Analytics":
    st.markdown('<div class="eyebrow">Deep dive</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Sales Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Explore daily, weekly, monthly, category, and product performance for the selected filters.</p>', unsafe_allow_html=True)
    st.write("")
    granularity = st.segmented_control("Time grain", ["Daily", "Weekly", "Monthly"], default="Daily") if hasattr(st, "segmented_control") else st.radio("Time grain", ["Daily", "Weekly", "Monthly"], horizontal=True)
    temp = df.copy()
    temp["Date"] = pd.to_datetime(temp["Date"])
    if granularity == "Daily":
        series = temp.groupby(temp["Date"].dt.date, as_index=False)["Revenue"].sum().rename(columns={"Date": "Period"})
    elif granularity == "Weekly":
        series = temp.assign(Period=temp["Date"].dt.to_period("W").dt.start_time).groupby("Period", as_index=False)["Revenue"].sum()
    else:
        series = temp.assign(Period=temp["Date"].dt.to_period("M").dt.start_time).groupby("Period", as_index=False)["Revenue"].sum()
    fig = px.line(series, x="Period", y="Revenue", markers=True, title=f"{granularity} revenue")
    fig.update_layout(template="plotly_white", height=390, margin=dict(l=10,r=10,t=55,b=10), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Category performance")
    cat = df.groupby("Category", as_index=False).agg(Revenue=("Revenue", "sum"), Units=("Quantity", "sum")).sort_values("Revenue", ascending=False)
    st.dataframe(cat, use_container_width=True, hide_index=True)

# ---------------------------- Dashboard ----------------------------
else:
    st.markdown(f'<div class="eyebrow">{"UrbanWear Sales Intelligence" if st.session_state.demo_mode else "Sales Intelligence"}</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="page-title">Turn Your Sales Data Into Decisions</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-subtitle">Upload your sales data and instantly discover what is driving your business.</p>', unsafe_allow_html=True)
    if st.session_state.demo_mode:
        st.caption("Demo Mode · UrbanWear · Realistic synthetic transactions")
    st.write("")
    if df.empty:
        st.warning("No transactions match the current filters. Try widening the date range or clearing a filter.")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: render_kpi("Total Revenue", money(summary["revenue"]))
    with k2: render_kpi("Total Orders", f"{summary['orders']:,}")
    with k3: render_kpi("Units Sold", f"{summary['units']:,}")
    with k4: render_kpi("Average Order Value", money(summary["aov"]))
    with k5: render_kpi("Growth vs Previous", f"{deltas['revenue_growth']:.1f}%", deltas["revenue_growth"])
    st.write("")

    left, right = st.columns([1.65, 1])
    with left:
        ts = df.copy()
        ts["Date"] = pd.to_datetime(ts["Date"])
        daily = ts.groupby("Date", as_index=False)["Revenue"].sum()
        fig = px.line(daily, x="Date", y="Revenue", markers=False, title="Revenue over time")
        fig.update_layout(template="plotly_white", height=370, margin=dict(l=10,r=10,t=55,b=10), hovermode="x unified", yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        cat = df.groupby("Category", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        fig = px.bar(cat, x="Revenue", y="Category", orientation="h", title="Sales by category")
        fig.update_layout(template="plotly_white", height=370, margin=dict(l=10,r=10,t=55,b=10), yaxis=dict(categoryorder="total ascending"), xaxis_tickprefix="$", xaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        prod = df.groupby("Product", as_index=False)["Revenue"].sum().nlargest(10, "Revenue").sort_values("Revenue")
        fig = px.bar(prod, x="Revenue", y="Product", orientation="h", title="Top 10 products")
        fig.update_layout(template="plotly_white", height=370, margin=dict(l=10,r=10,t=55,b=10), xaxis_tickprefix="$", xaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        weekday_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        wd = df.assign(Weekday=pd.to_datetime(df["Date"]).dt.day_name()).groupby("Weekday", as_index=False)["Revenue"].sum()
        wd["Weekday"] = pd.Categorical(wd["Weekday"], categories=weekday_order, ordered=True)
        wd = wd.sort_values("Weekday")
        fig = px.bar(wd, x="Weekday", y="Revenue", title="Revenue by weekday")
        fig.update_layout(template="plotly_white", height=370, margin=dict(l=10,r=10,t=55,b=10), yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        month = df.assign(Month=pd.to_datetime(df["Date"]).dt.strftime("%b")).groupby("Month", as_index=False)["Revenue"].sum()
        month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        month["Month"] = pd.Categorical(month["Month"], categories=month_order, ordered=True)
        fig = px.bar(month.sort_values("Month"), x="Month", y="Revenue", title="Revenue by month")
        fig.update_layout(template="plotly_white", height=340, margin=dict(l=10,r=10,t=55,b=10), yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        orders = df.assign(Date=pd.to_datetime(df["Date"])).groupby("Date")["Order ID"].nunique().reset_index(name="Orders")
        fig = px.line(orders, x="Date", y="Orders", title="Order volume over time")
        fig.update_layout(template="plotly_white", height=340, margin=dict(l=10,r=10,t=55,b=10), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    if "Region" in df.columns and not df.empty:
        region = df.groupby("Region", as_index=False)["Revenue"].sum().sort_values("Revenue", ascending=False)
        fig = px.bar(region, x="Region", y="Revenue", title="Regional performance")
        fig.update_layout(template="plotly_white", height=320, margin=dict(l=10,r=10,t=55,b=10), yaxis_tickprefix="$", yaxis_tickformat=",.0f")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### AI-style Business Insights")
    insights = generate_insights(df, prev_df)
    if insights:
        for item in insights:
            st.markdown(f'<div class="insight">{item}</div>', unsafe_allow_html=True)
    else:
        st.info("Not enough data to generate insights for this filter selection.")

    st.markdown("### Product Analysis")
    product_perf = build_product_performance(df)
    st.dataframe(product_perf, use_container_width=True, hide_index=True)

    st.markdown("### Export")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.download_button("Download cleaned data", raw.to_csv(index=False).encode("utf-8"), "insightdash_cleaned_data.csv", "text/csv", use_container_width=True)
    with e2:
        summary_export = pd.DataFrame([summary]).to_csv(index=False).encode("utf-8")
        st.download_button("Download summary report", summary_export, "insightdash_summary.csv", "text/csv", use_container_width=True)
    with e3:
        st.download_button("Download product performance", product_perf.to_csv(index=False).encode("utf-8"), "insightdash_product_performance.csv", "text/csv", use_container_width=True)

    with st.expander("Data quality & calculation notes"):
        st.write(f"Showing {len(df):,} transactions after filters. Revenue is calculated from Quantity × Unit Price when needed during ingestion. Duplicate rows and invalid dates are handled during upload.")
        if st.session_state.upload_warnings:
            for warning in st.session_state.upload_warnings:
                st.write(f"• {warning}")
