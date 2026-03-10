import io
import zipfile
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio
import requests
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Social Economics Visualizer", layout="wide")

st.title("🌍 Social Economics Visualizer (World Bank Live)")
st.caption("Gapminder-style explorer + country compare + export tools")

BASE_URL = "https://api.worldbank.org/v2"

# Curated indicators (fast defaults)
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


@st.cache_data(ttl=7 * 24 * 3600)
def fetch_indicator_catalog() -> pd.DataFrame:
    page = 1
    all_rows = []
    while True:
        url = f"{BASE_URL}/indicator?format=json&per_page=20000&page={page}"
        payload = requests.get(url, timeout=60).json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            break
        meta = payload[0]
        for item in payload[1]:
            name = item.get("name", "")
            code = item.get("id", "")
            source = (item.get("source") or {}).get("value", "")
            if code and name:
                all_rows.append(
                    {
                        "code": code,
                        "name": name,
                        "source": source,
                        "display": f"{name} [{code}]",
                    }
                )
        if page >= int(meta.get("pages", 1)):
            break
        page += 1

    return pd.DataFrame(all_rows).drop_duplicates(subset=["code"]) if all_rows else pd.DataFrame()


@st.cache_data(ttl=6 * 3600)
def fetch_indicator(indicator_code: str, start_year: int, end_year: int) -> pd.DataFrame:
    url = (
        f"{BASE_URL}/country/all/indicator/{indicator_code}"
        f"?format=json&date={start_year}:{end_year}&per_page=20000"
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
            rows.append({"countryiso3code": iso3, "Year": int(year), indicator_code: float(val)})
        except Exception:
            continue

    return pd.DataFrame(rows)


@st.cache_data(ttl=6 * 3600)
def build_dataset(indicator_codes: tuple, start_year: int, end_year: int) -> pd.DataFrame:
    countries = fetch_countries()

    merged = None
    for code in indicator_codes:
        dfi = fetch_indicator(code, start_year, end_year)
        merged = dfi if merged is None else merged.merge(dfi, on=["countryiso3code", "Year"], how="outer")

    if merged is None:
        return pd.DataFrame()

    merged = merged.merge(countries, on="countryiso3code", how="left")
    merged = merged.dropna(subset=["Country", "Year"])
    merged["Year"] = merged["Year"].astype(int)
    return merged


def make_pdf_summary(title: str, lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, title)
    y -= 25
    c.setFont("Helvetica", 10)
    for line in lines:
        if y < 40:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = h - 40
        c.drawString(40, y, line[:120])
        y -= 15
    c.save()
    buffer.seek(0)
    return buffer.read()


# ---------- UI ----------
with st.sidebar:
    st.header("Data settings")
    year_min = st.number_input("Start year", min_value=1960, max_value=2025, value=1990, step=1)
    year_max = st.number_input("End year", min_value=1960, max_value=2025, value=2023, step=1)
    if year_min > year_max:
        st.error("Start year must be <= End year")
        st.stop()

    use_catalog = st.checkbox("Use full World Bank indicator catalog", value=False)

# indicator label maps
if use_catalog:
    catalog = fetch_indicator_catalog()
    if catalog.empty:
        st.error("Could not load World Bank indicator catalog.")
        st.stop()
    label_list = catalog["display"].tolist()
    reverse_map = {row.display: row.code for row in catalog.itertuples(index=False)}

    default_x_label = next((d for d in label_list if DEFAULT_X in d), label_list[0])
    default_y_label = next((d for d in label_list if DEFAULT_Y in d), label_list[min(1, len(label_list)-1)])
    default_size_label = next((d for d in label_list if DEFAULT_SIZE in d), label_list[min(2, len(label_list)-1)])
else:
    label_list = list(INDICATORS.values())
    reverse_map = {v: k for k, v in INDICATORS.items()}
    default_x_label = INDICATORS[DEFAULT_X]
    default_y_label = INDICATORS[DEFAULT_Y]
    default_size_label = INDICATORS[DEFAULT_SIZE]

with st.sidebar:
    st.header("Axes")
    x_label = st.selectbox("X axis", options=label_list, index=label_list.index(default_x_label))
    y_label = st.selectbox("Y axis", options=label_list, index=label_list.index(default_y_label))
    size_label = st.selectbox("Bubble size", options=["(none)"] + label_list, index=1 + label_list.index(default_size_label))

    color_by = st.selectbox("Color by", options=["Country", "Region", "IncomeGroup", "LendingType"], index=0)
    log_x = st.checkbox("Log scale for X axis", value=True)
    show_trails = st.checkbox("Show country trails", value=False)

x_code = reverse_map[x_label]
y_code = reverse_map[y_label]
needed_codes = {x_code, y_code}
size_code = None
if size_label != "(none)":
    size_code = reverse_map[size_label]
    needed_codes.add(size_code)

# compare mode indicator
with st.sidebar:
    st.header("Compare mode")
    compare_mode = st.checkbox("Enable country compare lines", value=True)
    compare_label = st.selectbox("Compare indicator", options=label_list, index=label_list.index(y_label))
compare_code = reverse_map[compare_label]
needed_codes.add(compare_code)

df = build_dataset(tuple(sorted(needed_codes)), int(year_min), int(year_max))
if df.empty:
    st.error("No data returned from World Bank API for current settings.")
    st.stop()

# Pretty names for selected indicators
rename_map = {
    x_code: x_label,
    y_code: y_label,
    compare_code: compare_label,
}
if size_code:
    rename_map[size_code] = size_label

df = df.rename(columns=rename_map)

all_countries = sorted(df["Country"].dropna().unique())
default_focus = [c for c in ["China", "United States", "Japan", "Germany", "India"] if c in all_countries]

with st.sidebar:
    country_filter = st.multiselect(
        "Countries to compare (choose one or more)",
        options=all_countries,
        default=default_focus,
    )

if country_filter:
    df = df[df["Country"].isin(country_filter)]
    if df.empty:
        st.warning("No data after country filter.")
        st.stop()

required = [x_label, y_label]
if size_code:
    required.append(size_label)
plot_df = df.dropna(subset=required)

if plot_df.empty:
    st.warning("No complete observations for selected indicators.")
    st.stop()

# ---------- Main Gapminder-style bubble chart ----------
scatter_kwargs = dict(
    data_frame=plot_df,
    x=x_label,
    y=y_label,
    animation_frame="Year",
    animation_group="Country",
    color=color_by,
    hover_name="Country",
    title="Gapminder-style Social & Economic Time Series",
)

if size_code:
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

# ---------- Compare mode ----------
if compare_mode:
    st.subheader("Country Compare Mode")
    countries = sorted(plot_df["Country"].dropna().unique())
    default_compare = [c for c in ["China", "United States", "Japan", "Germany", "India"] if c in countries]
    selected_countries = st.multiselect(
        "Select countries to compare",
        options=countries,
        default=default_compare[:5],
    )

    comp_df = df[df["Country"].isin(selected_countries)].dropna(subset=[compare_label])
    if not comp_df.empty and selected_countries:
        comp_fig = px.line(
            comp_df.sort_values(["Country", "Year"]),
            x="Year",
            y=compare_label,
            color="Country",
            markers=True,
            title=f"Compare over time: {compare_label}",
        )
        comp_fig.update_layout(template="plotly_white", height=480)
        st.plotly_chart(comp_fig, use_container_width=True)
    else:
        st.info("Select countries with available data to compare.")

# ---------- Snapshot ----------
st.subheader("Data snapshot")
year_options = sorted(plot_df["Year"].unique())
selected_year = st.selectbox("Select year", options=year_options, index=len(year_options) - 1)

view_cols = ["Country", "Region", "IncomeGroup", x_label, y_label]
if size_code:
    view_cols.append(size_label)
snapshot = plot_df[plot_df["Year"] == selected_year][view_cols].sort_values(x_label, ascending=False)
st.dataframe(snapshot, use_container_width=True)

# ---------- Export ----------
st.subheader("Export")
export_col1, export_col2, export_col3 = st.columns(3)

with export_col1:
    csv_bytes = snapshot.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download snapshot CSV",
        data=csv_bytes,
        file_name=f"snapshot_{selected_year}.csv",
        mime="text/csv",
    )

with export_col2:
    pdf_lines = [
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"Year range: {year_min}-{year_max}",
        f"X: {x_label}",
        f"Y: {y_label}",
        f"Bubble size: {size_label}",
        f"Color: {color_by}",
        f"Countries: {', '.join(country_filter) if country_filter else 'All'}",
        f"Snapshot year: {selected_year}",
        f"Rows in snapshot: {len(snapshot)}",
    ]
    pdf_bytes = make_pdf_summary("Social Economics Visualizer - Summary", pdf_lines)
    st.download_button(
        "Download summary PDF",
        data=pdf_bytes,
        file_name="summary_report.pdf",
        mime="application/pdf",
    )

with export_col3:
    # One-click ZIP (CSV + PDF + optional PNG)
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"snapshot_{selected_year}.csv", csv_bytes)
        zf.writestr("summary_report.pdf", pdf_bytes)
        try:
            png = pio.to_image(fig, format="png", width=1400, height=900, scale=2)
            zf.writestr("main_chart.png", png)
        except Exception:
            zf.writestr("main_chart.txt", "PNG export unavailable (install kaleido).")

    zbuf.seek(0)
    st.download_button(
        "One-click export ZIP",
        data=zbuf.getvalue(),
        file_name="social_economics_export.zip",
        mime="application/zip",
    )

st.caption("Data source: World Bank API live data. Tip: enable full catalog to search/select from the full indicator universe.")
