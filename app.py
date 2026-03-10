import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Social Economics Visualizer", layout="wide")

st.title("🌍 Social Economics Visualizer (World Bank Live)")
st.caption("Gapminder-style explorer powered by live World Bank indicators")

BASE_URL = "https://api.worldbank.org/v2"

# A broad starter set of socioeconomic indicators (expand anytime)
INDICATORS = {
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "NY.GDP.PCAP.PP.CD": "GDP per capita, PPP (current international $)",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.PP.CD": "GDP, PPP (current international $)",
    "NY.GDP.PCAP.KD": "GDP per capita (constant 2015 US$)",
    "SP.DYN.LE00.IN": "Life expectancy at birth, total (years)",
    "SP.POP.TOTL": "Population, total",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total population)",
    "SP.DYN.TFRT.IN": "Fertility rate, total (births per woman)",
    "SP.DYN.IMRT.IN": "Mortality rate, infant (per 1,000 live births)",
    "SI.POV.GINI": "Gini index",
    "SI.POV.NAHC": "Poverty headcount ratio at national poverty lines (% of population)",
    "SE.ADT.LITR.ZS": "Literacy rate, adult total (% of people ages 15 and above)",
    "SE.XPD.TOTL.GD.ZS": "Government expenditure on education, total (% of GDP)",
    "SH.XPD.CHEX.GD.ZS": "Current health expenditure (% of GDP)",
    "SH.XPD.CHEX.PC.CD": "Current health expenditure per capita (current US$)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of total labor force)",
    "SL.TLF.CACT.ZS": "Labor force participation rate, total (% of total population ages 15+)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "Foreign direct investment, net inflows (% of GDP)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt, total (% of GDP)",
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "EN.ATM.CO2E.PC": "CO2 emissions (metric tons per capita)",
    "EG.USE.PCAP.KG.OE": "Energy use (kg of oil equivalent per capita)",
    "EN.POP.DNST": "Population density (people per sq. km of land area)",
}

DEFAULT_X = "NY.GDP.PCAP.PP.CD"
DEFAULT_Y = "SP.DYN.LE00.IN"
DEFAULT_SIZE = "SP.POP.TOTL"


@st.cache_data(ttl=24 * 3600)
def fetch_countries() -> pd.DataFrame:
    url = f"{BASE_URL}/country?format=json&per_page=400"
    data = requests.get(url, timeout=30).json()
    rows = data[1]
    out = []
    for r in rows:
        # Skip aggregates like 'World', 'High income', etc.
        if r.get("region", {}).get("id") == "NA":
            continue
        out.append(
            {
                "countryiso3code": r.get("id"),
                "Country": r.get("name"),
                "Region": r.get("region", {}).get("value"),
                "IncomeGroup": r.get("incomeLevel", {}).get("value"),
                "LendingType": r.get("lendingType", {}).get("value"),
            }
        )
    return pd.DataFrame(out)


@st.cache_data(ttl=6 * 3600)
def fetch_indicator(indicator_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    per_page = 20000
    url = (
        f"{BASE_URL}/country/all/indicator/{indicator_code}"
        f"?format=json&date={start_year}:{end_year}&per_page={per_page}"
    )
    payload = requests.get(url, timeout=60).json()

    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        return pd.DataFrame(columns=["countryiso3code", "Year", indicator_code])

    rows = []
    for item in payload[1]:
        iso3 = item.get("countryiso3code")
        val = item.get("value")
        year = item.get("date")
        if not iso3 or val is None:
            continue
        try:
            year = int(year)
            val = float(val)
        except Exception:
            continue
        rows.append({"countryiso3code": iso3, "Year": year, indicator_code: val})

    return pd.DataFrame(rows)


@st.cache_data(ttl=6 * 3600)
def build_dataset(indicator_codes: tuple, start_year: int, end_year: int) -> pd.DataFrame:
    countries = fetch_countries()

    merged = None
    for code in indicator_codes:
        dfi = fetch_indicator(code, start_year, end_year)
        if merged is None:
            merged = dfi
        else:
            merged = merged.merge(dfi, on=["countryiso3code", "Year"], how="outer")

    if merged is None:
        return pd.DataFrame()

    merged = merged.merge(countries, on="countryiso3code", how="left")
    merged = merged.dropna(subset=["Country", "Year"])
    merged["Year"] = merged["Year"].astype(int)

    # User-friendly labels
    rename_map = {k: v for k, v in INDICATORS.items()}
    merged = merged.rename(columns=rename_map)

    return merged


with st.sidebar:
    st.header("Data settings")
    year_min = st.number_input("Start year", min_value=1960, max_value=2025, value=1990, step=1)
    year_max = st.number_input("End year", min_value=1960, max_value=2025, value=2023, step=1)
    if year_min > year_max:
        st.error("Start year must be <= End year")
        st.stop()

    st.header("Axes")
    label_list = list(INDICATORS.values())
    reverse_map = {v: k for k, v in INDICATORS.items()}

    x_label = st.selectbox(
        "X axis",
        options=label_list,
        index=label_list.index(INDICATORS[DEFAULT_X]),
    )
    y_label = st.selectbox(
        "Y axis",
        options=label_list,
        index=label_list.index(INDICATORS[DEFAULT_Y]),
    )
    size_label = st.selectbox(
        "Bubble size",
        options=["(none)"] + label_list,
        index=1 + label_list.index(INDICATORS[DEFAULT_SIZE]),
    )

    color_by = st.selectbox("Color by", options=["Region", "IncomeGroup", "LendingType"], index=0)
    log_x = st.checkbox("Log scale for X axis", value=True)
    show_trails = st.checkbox("Show country trails", value=False)

needed_codes = {reverse_map[x_label], reverse_map[y_label]}
if size_label != "(none)":
    needed_codes.add(reverse_map[size_label])

df = build_dataset(tuple(sorted(needed_codes)), int(year_min), int(year_max))

if df.empty:
    st.error("No data returned from World Bank API for current settings.")
    st.stop()

# Region options after data load
all_regions = sorted([r for r in df["Region"].dropna().unique()])
with st.sidebar:
    region_filter = st.multiselect("Region", options=all_regions, default=all_regions)

df = df[df["Region"].isin(region_filter)]

if df.empty:
    st.warning("No data after filters.")
    st.stop()

# Keep rows with required axes
required = [x_label, y_label]
if size_label != "(none)":
    required.append(size_label)
plot_df = df.dropna(subset=required)

if plot_df.empty:
    st.warning("No complete observations for selected indicators and years.")
    st.stop()

scatter_kwargs = dict(
    data_frame=plot_df,
    x=x_label,
    y=y_label,
    animation_frame="Year",
    animation_group="Country",
    color=color_by,
    hover_name="Country",
    hover_data={"countryiso3code": True, "Year": True, x_label: ':.2f', y_label: ':.2f'},
    title="Gapminder-style Social & Economic Time Series",
)

if size_label != "(none)":
    scatter_kwargs["size"] = size_label
    scatter_kwargs["size_max"] = 55

fig = px.scatter(**scatter_kwargs)
fig.update_layout(template="plotly_white", height=720)
if log_x:
    fig.update_xaxes(type="log")

if show_trails:
    trails = px.line(
        plot_df.sort_values(["Country", "Year"]),
        x=x_label,
        y=y_label,
        color="Country",
        line_group="Country",
    )
    for t in trails.data:
        t.update(showlegend=False, opacity=0.15)
        fig.add_trace(t)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Data snapshot")
year_options = sorted(plot_df["Year"].unique())
selected_year = st.selectbox("Select year", options=year_options, index=len(year_options) - 1)
view_cols = ["Country", "Region", "IncomeGroup", x_label, y_label]
if size_label != "(none)":
    view_cols.append(size_label)

snapshot = plot_df[plot_df["Year"] == selected_year][view_cols].sort_values(x_label, ascending=False)
st.dataframe(snapshot, use_container_width=True)

st.caption(
    "Data source: World Bank API (live). Indicator list is intentionally broad and can be extended with more WDI codes."
)
