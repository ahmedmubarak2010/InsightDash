# InsightDash

**InsightDash** is a production-quality Streamlit MVP for small-business sales analytics. The dashboard is the product: it ships with a realistic UrbanWear demo dataset, automatic CSV/XLSX ingestion, data cleaning, interactive filters, Plotly charts, business insights, product analysis, and CSV exports.

## Features

- UrbanWear demo mode with 1,200 realistic transactions
- CSV and XLSX upload with automatic column-name detection
- Revenue fallback: `Quantity × Unit Price`
- Safe cleaning of dates, numeric fields, duplicates, and missing optional fields
- Date, product, category, and sales-channel filters
- Revenue, orders, units, AOV, and period-growth KPIs
- Revenue trend, category, product, weekday, monthly, order-volume, and regional charts
- Algorithmic AI-style business insights without an external API
- Sortable/filterable Streamlit data table for product performance
- Cleaned-data, summary, and product-performance CSV exports
- No database or API keys required

## Local setup

Python 3.10+ is recommended.

```bash
git clone https://github.com/ahmedmubarak2010/InsightDash.git
cd InsightDash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Replit deployment

1. Create a new Replit app from the GitHub repository (or import the repo).
2. Make sure `requirements.txt` is present; Replit will install the dependencies.
3. Run `streamlit run app.py --server.address 0.0.0.0 --server.port 3000`.
4. Set the Replit webview/port to `3000` if Replit asks for a port.
5. No secrets are required.

For a production client demo, keep the repository public or configure the appropriate private-repository access in Replit.

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, create a new app.
3. Select `ahmedmubarak2010/InsightDash`.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Deploy.

Streamlit Cloud installs packages from `requirements.txt`. No environment variables are needed for the MVP.

## Expected upload columns

The loader recognizes common variants of:

`Date`, `Product`, `Category`, `Quantity`, `Unit Price`, `Revenue`, `Customer`, `Salesperson`, `Region`, `Order ID`, and `Sales Channel`.

At minimum, a file needs a date plus product and either revenue or quantity + unit price. Optional columns are safely filled or generated when absent.

## Project structure

```text
InsightDash/
├── app.py
├── requirements.txt
├── README.md
└── utils/
    ├── __init__.py
    ├── data_loader.py
    ├── analytics.py
    └── insights.py
```

## Notes

This MVP intentionally keeps uploaded data in Streamlit session state and does not persist customer data. The demo dataset is synthetic and should not be presented as real business data.
