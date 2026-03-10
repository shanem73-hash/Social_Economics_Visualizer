# Social Economics Visualizer

A Streamlit app inspired by Gapminder to visualize time-series changes in:
- **GDP per capita** (x-axis, log scale)
- **Life expectancy** (y-axis)
- **Population** (bubble size)
- **Continent** (color)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

- Animated bubble chart over years
- Continent filter
- Year-range filter
- Optional country trails
- Year snapshot table

## Data source

Uses Plotly's built-in Gapminder dataset (`plotly.express.data.gapminder`).
