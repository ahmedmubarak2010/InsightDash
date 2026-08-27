import pandas as pd


def _pct(v):
    return f"{v:.1f}%"


def generate_insights(df, prev_df):
    if df is None or df.empty:
        return []
    out = []
    product = df.groupby("Product").agg(Revenue=("Revenue", "sum"), Units=("Quantity", "sum")).sort_values("Revenue", ascending=False)
    category = df.groupby("Category")["Revenue"].sum().sort_values(ascending=False)
    weekday = df.assign(Weekday=pd.to_datetime(df["Date"]).dt.day_name()).groupby("Weekday")["Revenue"].sum()
    if len(product):
        best = product.index[0]
        out.append(f"<b>{best}</b> is your top revenue product at ${product.iloc[0]['Revenue']:,.0f}.")
    if len(category):
        out.append(f"<b>{category.index[0]}</b> is the highest-revenue category, contributing ${category.iloc[0]:,.0f}.")
    if len(weekday):
        best_day, low_day = weekday.idxmax(), weekday.idxmin()
        out.append(f"<b>{best_day}</b> is your strongest sales day, while <b>{low_day}</b> is the weakest.")
    total = product["Revenue"].sum()
    if total and len(product) >= 3:
        top3 = product.head(3)["Revenue"].sum() / total * 100
        out.append(f"Your top 3 products account for <b>{top3:.1f}%</b> of filtered revenue.")
    if prev_df is not None and not prev_df.empty:
        cur = df["Revenue"].sum(); prev = prev_df["Revenue"].sum()
        growth = ((cur - prev) / prev * 100) if prev else 100
        direction = "increased" if growth >= 0 else "decreased"
        out.append(f"Revenue <b>{direction} {_pct(abs(growth))}</b> compared with the previous equivalent period.")
    # Product momentum: compare first vs second half of selected dates.
    dates = pd.to_datetime(df["Date"])
    midpoint = dates.min() + (dates.max() - dates.min()) / 2
    first = df[dates <= midpoint].groupby("Product")["Revenue"].sum()
    second = df[dates > midpoint].groupby("Product")["Revenue"].sum()
    common = first.index.intersection(second.index)
    if len(common):
        momentum = ((second[common] + 1) / (first[common] + 1) - 1) * 100
        declining = momentum.sort_values().head(1)
        if len(declining) and declining.iloc[0] < -10:
            out.append(f"<b>{declining.index[0]}</b> shows the clearest decline across the selected period ({declining.iloc[0]:.1f}%).")
    return out[:7]
