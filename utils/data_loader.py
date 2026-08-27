import io
import re

import numpy as np
import pandas as pd

COLUMN_ALIASES = {
    "Date": ["date", "order date", "transaction date", "sale date", "created at", "timestamp"],
    "Product": ["product", "product name", "item", "item name", "sku name"],
    "Category": ["category", "product category", "department", "type"],
    "Quantity": ["quantity", "qty", "units", "units sold", "count"],
    "Unit Price": ["unit price", "price", "selling price", "unit cost", "sale price"],
    "Revenue": ["revenue", "sales", "sales amount", "total sales", "amount", "total", "net sales"],
    "Customer": ["customer", "customer name", "client", "buyer"],
    "Salesperson": ["salesperson", "sales person", "seller", "representative", "rep"],
    "Region": ["region", "area", "territory", "location", "market"],
    "Order ID": ["order id", "order_id", "order number", "order no", "invoice", "transaction id"],
    "Sales Channel": ["sales channel", "channel", "source", "order channel", "platform"],
}


def _norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def detect_columns(columns):
    normalized = {_norm(c): c for c in columns}
    mapping = {}
    used = set()
    for canonical, aliases in COLUMN_ALIASES.items():
        candidates = [canonical] + aliases
        for alias in candidates:
            key = _norm(alias)
            if key in normalized and normalized[key] not in used:
                mapping[canonical] = normalized[key]
                used.add(normalized[key])
                break
        if canonical in mapping:
            continue
        for norm_col, original in normalized.items():
            if original in used:
                continue
            if any(a in norm_col or norm_col in a for a in map(_norm, candidates)):
                mapping[canonical] = original
                used.add(original)
                break
    return mapping


def _read_file(uploaded_file):
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("The uploaded file is empty.")
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(raw))
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    if name.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    raise ValueError("Unsupported file type. Please upload CSV or XLSX.")


def clean_and_standardize(df):
    warnings = []
    if df is None or df.empty:
        raise ValueError("The uploaded file contains no rows.")
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapping = detect_columns(df.columns)
    rename = {source: canonical for canonical, source in mapping.items()}
    df = df.rename(columns=rename)

    if "Date" not in df.columns:
        raise ValueError("Could not detect a date column. Please include a column such as Date or Order Date.")
    if "Product" not in df.columns:
        raise ValueError("Could not detect a product column. Please include a column such as Product or Item.")
    if "Quantity" not in df.columns and "Revenue" not in df.columns:
        raise ValueError("Could not detect Quantity or Revenue. At least one is required for sales analysis.")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    bad_dates = int(df["Date"].isna().sum())
    if bad_dates:
        warnings.append(f"Removed {bad_dates:,} rows with invalid or missing dates.")
        df = df.dropna(subset=["Date"])

    if "Quantity" in df.columns:
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    if "Unit Price" in df.columns:
        df["Unit Price"] = pd.to_numeric(df["Unit Price"], errors="coerce")
    if "Revenue" in df.columns:
        df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")

    if "Revenue" not in df.columns:
        if "Quantity" not in df.columns or "Unit Price" not in df.columns:
            raise ValueError("Revenue is missing, and Quantity + Unit Price were not both detected.")
        df["Revenue"] = df["Quantity"] * df["Unit Price"]
        warnings.append("Revenue was calculated as Quantity × Unit Price.")
    elif "Quantity" in df.columns and "Unit Price" not in df.columns:
        warnings.append("Unit Price was not detected; uploaded Revenue was used as-is.")

    if "Quantity" not in df.columns:
        df["Quantity"] = 1
        warnings.append("Quantity was not detected; each row was treated as one unit.")
    if "Unit Price" not in df.columns:
        df["Unit Price"] = np.where(df["Quantity"].fillna(0) != 0, df["Revenue"] / df["Quantity"], 0)

    df["Product"] = df["Product"].fillna("Unknown Product").astype(str).str.strip()
    if "Category" not in df.columns:
        df["Category"] = "Uncategorized"
        warnings.append("Category was not detected; rows were grouped as Uncategorized.")
    else:
        df["Category"] = df["Category"].fillna("Uncategorized").astype(str).str.strip()
    if "Order ID" not in df.columns:
        df["Order ID"] = [f"ROW-{i:07d}" for i in range(len(df))]
        warnings.append("Order ID was not detected; unique row IDs were generated for order counting.")

    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    removed_dupes = before - len(df)
    if removed_dupes:
        warnings.append(f"Removed {removed_dupes:,} exact duplicate rows.")

    df["Quantity"] = df["Quantity"].fillna(0).clip(lower=0)
    df["Revenue"] = df["Revenue"].fillna(0).clip(lower=0)
    df["Unit Price"] = df["Unit Price"].fillna(0).clip(lower=0)

    if "Sales Channel" in df.columns:
        df["Sales Channel"] = df["Sales Channel"].fillna("Unknown").astype(str).str.strip()
    for optional in ["Customer", "Salesperson", "Region"]:
        if optional in df.columns:
            df[optional] = df[optional].fillna("Unknown").astype(str).str.strip()

    preferred = ["Date", "Product", "Category", "Quantity", "Unit Price", "Revenue", "Customer", "Salesperson", "Region", "Sales Channel", "Order ID"]
    ordered = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    return df[ordered], mapping, warnings


def load_uploaded_file(uploaded_file):
    try:
        raw = _read_file(uploaded_file)
        data, mapping, warnings = clean_and_standardize(raw)
        if data.empty:
            return {"data": None, "mapping": mapping, "warnings": warnings, "error": "No valid transactions remained after cleaning."}
        return {"data": data, "mapping": mapping, "warnings": warnings, "error": None}
    except Exception as exc:
        return {"data": None, "mapping": {}, "warnings": [], "error": str(exc)}


def generate_demo_data(n=1200, seed=42):
    rng = np.random.default_rng(seed)
    products = {
        "T-Shirts": ("Apparel", 24, 1.25), "Jeans": ("Apparel", 59, 0.95), "Sneakers": ("Footwear", 79, 1.10),
        "Hoodies": ("Apparel", 64, 0.92), "Jackets": ("Outerwear", 109, 0.72), "Caps": ("Accessories", 19, 0.85),
        "Bags": ("Accessories", 49, 0.78), "Sports Shoes": ("Footwear", 92, 1.18), "Watches": ("Accessories", 129, 0.58), "Accessories": ("Accessories", 14, 1.30),
    }
    names = ["Liam Carter","Noah Wilson","Mia Johnson","Emma Davis","Olivia Smith","Ethan Brown","Ava Miller","Lucas Taylor","Sophia Moore","James Anderson","Amelia Thomas","Henry Jackson","Isla White","Leo Harris","Grace Martin"]
    regions = ["Cairo", "Alexandria", "Delta", "Canal", "Upper Egypt"]
    channels = ["Store", "Website", "Instagram", "Marketplace"]
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=365)
    dates = pd.date_range(start, end, freq="D")
    day_weights = np.array([0.9 + 0.0025*i for i in range(len(dates))])
    day_weights *= np.where(dates.dayofweek >= 4, 1.20, 1.0)
    chosen_dates = rng.choice(dates, size=n, p=day_weights / day_weights.sum())
    product_names = list(products)
    base_probs = np.array([1.35, 1.0, 1.25, 1.05, .65, .9, .8, 1.05, .55, 1.25])
    product_choices = rng.choice(product_names, size=n, p=base_probs / base_probs.sum())
    rows = []
    for i, (d, p) in enumerate(zip(chosen_dates, product_choices), 1):
        d = pd.Timestamp(d)
        category, base_price, demand = products[p]
        qty = int(rng.choice([1,2,3,4,5], p=[.40,.30,.18,.08,.04]) * demand)
        qty = max(1, qty)
        seasonal = 1 + 0.05 * np.sin(2 * np.pi * d.dayofyear / 365)
        price = round(base_price * rng.normal(1.0, 0.045) * seasonal, 2)
        rows.append({
            "Date": d.date(), "Product": p, "Category": category, "Quantity": qty,
            "Unit Price": price, "Revenue": round(qty * price, 2), "Customer": rng.choice(names),
            "Salesperson": f"Rep {rng.integers(1, 9)}", "Region": rng.choice(regions, p=[.32,.20,.22,.12,.14]),
            "Sales Channel": rng.choice(channels, p=[.38,.28,.18,.16]), "Order ID": f"UW-{i:06d}"
        })
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
