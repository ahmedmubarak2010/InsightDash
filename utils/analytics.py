import pandas as pd


def safe_date_range(df):
    dates = pd.to_datetime(df.get("Date"), errors="coerce").dropna()
    if dates.empty:
        today = pd.Timestamp.today().date()
        return today, today
    return dates.min().date(), dates.max().date()


def build_summary(df):
    if df is None or df.empty:
        return {"revenue": 0.0, "orders": 0, "units": 0.0, "aov": 0.0}
    revenue = float(df["Revenue"].sum())
    orders = int(df["Order ID"].nunique()) if "Order ID" in df else len(df)
    units = float(df["Quantity"].sum())
    return {"revenue": revenue, "orders": orders, "units": units, "aov": revenue / orders if orders else 0.0}


def previous_period_metrics(current, previous):
    def growth(a, b):
        if b == 0:
            return 100.0 if a > 0 else 0.0
        return ((a - b) / b) * 100
    return {"revenue_growth": growth(current["revenue"], previous["revenue"]), "orders_growth": growth(current["orders"], previous["orders"]), "units_growth": growth(current["units"], previous["units"]), "aov_growth": growth(current["aov"], previous["aov"])}


def build_product_performance(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["Product", "Category", "Units Sold", "Revenue", "Average Price", "Revenue %", "Rank"])
    g = df.groupby(["Product", "Category"], as_index=False).agg(**{"Units Sold": ("Quantity", "sum"), "Revenue": ("Revenue", "sum"), "Average Price": ("Unit Price", "mean")})
    total = g["Revenue"].sum()
    g["Revenue %"] = (g["Revenue"] / total * 100).round(1) if total else 0
    g = g.sort_values("Revenue", ascending=False).reset_index(drop=True)
    g["Rank"] = g.index + 1
    g["Revenue"] = g["Revenue"].round(2)
    g["Average Price"] = g["Average Price"].round(2)
    g["Units Sold"] = g["Units Sold"].round(0).astype(int)
    return g
