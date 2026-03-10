# Social Economics Visualizer (World Bank Live)

A Streamlit app inspired by Gapminder, powered by **live World Bank API data**.

## What it visualizes

- Animated bubble chart over time
- X-axis: selectable socioeconomic indicator
- Y-axis: selectable socioeconomic indicator
- Bubble size: selectable indicator (or none)
- Color by: Region / Income Group / Lending Type

## Included indicator families (broad set)

- GDP / GDP per capita (nominal, real, PPP)
- Life expectancy, fertility, infant mortality
- Population, urbanization, population density
- Poverty / inequality (Gini)
- Education / health spending
- Unemployment / labor participation
- Inflation, debt, trade, FDI
- Internet usage, CO2, energy use

> You can easily add more WDI indicators by extending the `INDICATORS` dictionary in `app.py`.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data source

- World Bank API: `https://api.worldbank.org/v2`
- Country metadata + indicator time series fetched live and cached in Streamlit.
