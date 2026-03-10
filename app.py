import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Social Economics Visualizer", layout="wide")

st.title("🌍 Social Economics Visualizer")
st.caption("Gapminder-style interactive view of GDP per capita vs Life Expectancy over time")

@st.cache_data
def load_data() -> pd.DataFrame:
    df = px.data.gapminder()
    df = df.rename(columns={
        "gdpPercap": "GDP per capita",
        "lifeExp": "Life expectancy",
        "pop": "Population",
        "country": "Country",
        "continent": "Continent",
        "year": "Year",
    })
    return df


df = load_data()

with st.sidebar:
    st.header("Filters")
    continents = sorted(df["Continent"].unique())
    selected_continents = st.multiselect(
        "Continent",
        options=continents,
        default=continents,
    )

    year_min = int(df["Year"].min())
    year_max = int(df["Year"].max())
    year_range = st.slider("Year range", min_value=year_min, max_value=year_max, value=(year_min, year_max), step=5)

    show_trails = st.checkbox("Show country trails", value=False)

filtered = df[
    (df["Continent"].isin(selected_continents))
    & (df["Year"] >= year_range[0])
    & (df["Year"] <= year_range[1])
]

if filtered.empty:
    st.warning("No data in current filter. Please adjust filters.")
    st.stop()

fig = px.scatter(
    filtered,
    x="GDP per capita",
    y="Life expectancy",
    animation_frame="Year",
    animation_group="Country",
    size="Population",
    color="Continent",
    hover_name="Country",
    size_max=60,
    log_x=True,
    range_x=[max(100, filtered["GDP per capita"].min() * 0.8), filtered["GDP per capita"].max() * 1.1],
    range_y=[filtered["Life expectancy"].min() - 2, filtered["Life expectancy"].max() + 2],
    labels={
        "GDP per capita": "GDP per capita (log scale)",
        "Life expectancy": "Life expectancy (years)",
    },
    title="GDP per capita vs Life expectancy",
)

fig.update_layout(
    legend_title_text="Continent",
    template="plotly_white",
    height=700,
)

if show_trails:
    trails = px.line(
        filtered,
        x="GDP per capita",
        y="Life expectancy",
        color="Country",
        line_group="Country",
        hover_name="Country",
    )
    for trace in trails.data:
        trace.update(showlegend=False, opacity=0.18)
        fig.add_trace(trace)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Snapshot table")
selected_year = st.selectbox("Pick a year", sorted(filtered["Year"].unique()))
current = filtered[filtered["Year"] == selected_year].sort_values("GDP per capita", ascending=False)
st.dataframe(
    current[["Country", "Continent", "GDP per capita", "Life expectancy", "Population"]],
    use_container_width=True,
)
