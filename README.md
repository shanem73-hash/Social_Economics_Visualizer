# Social Economics Visualizer (World Bank Live)

A Streamlit app inspired by Gapminder, powered by **live World Bank API data**.

## Key features

### 1) Gapminder-style animated bubble chart
- Time animation by year
- X/Y indicator selection
- Optional bubble size indicator
- Color by Region / Income Group / Lending Type
- Optional country trails

### 2) Real World Bank live indicator data
- Pulls from `https://api.worldbank.org/v2`
- Includes a broad curated indicator set (GDP, PPP, health, education, labor, trade, inflation, debt, climate, etc.)
- Optional **full World Bank indicator catalog mode** for dynamic indicator search/selection

### 3) Country compare mode
- Pick multiple countries
- Plot indicator trend lines over time (line chart)

### 4) Export tools
- Download snapshot CSV
- Download summary PDF
- One-click ZIP export with:
  - CSV snapshot
  - PDF summary
  - PNG chart (fallback text note if PNG engine unavailable)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes

- Indicator availability varies by country/year.
- Full catalog mode is larger and can be slower on first load.
