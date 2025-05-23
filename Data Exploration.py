# Data Exploration.py

import streamlit as st
import pandas as pd
import os
from streamlit_echarts import st_echarts
import yfinance as yf

# ------------------------------------------------------------------------------
# Page config
# ------------------------------------------------------------------------------
st.set_page_config(layout="wide")

# ------------------------------------------------------------------------------
# App‐level password gate
# ------------------------------------------------------------------------------
password = st.text_input("Enter password", type="password")
if password != "ffd":
    st.warning("🔒 Please enter the password to continue.")
    st.stop()

# ------------------------------------------------------------------------------
# 0. Full-width layout + CSS tweaks
# ------------------------------------------------------------------------------
st.markdown("""
<style>
/* Remove default Streamlit image shadows */
.stImage > div {
    box-shadow: none !important;
}
/* Center each button */
.stButton button {
    display: block;
    margin-left: auto;
    margin-right: auto;
}
/* Ticker tape styling */
.ticker-wrap {
    width: 60%;
    margin: 1rem auto;
    overflow: hidden;
    background: #f5f5f5;
    border-top: 1px solid #ddd;
    border-bottom: 1px solid #ddd;
    padding: 0.5rem 0;
}
.ticker {
    display: inline-block;
    white-space: nowrap;
    padding-left: 100%;
    animation: scroll 40s linear infinite;
}
.ticker__item {
    display: inline-block;
    padding: 0 2rem;
    font-size: 1.1rem;
    color: #333;
}
@keyframes scroll {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-100%); }
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Load and cache live commodity prices + change percent up front
# ------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_commodity_data():
    tickers = {
        "Rice":         "ZR=F",
        "Wheat":        "ZW=F",
        "Maize":        "ZC=F",
        "Soybeans":     "ZS=F",
        "Soybean Oil":  "ZL=F",
        "Soybean Meal": "ZM=F",
        "Sugar":        "SB=F",
        "Meat, beef":   "LE=F",
        "Oranges":      "OJ=F",
        "Coffee":       "KC=F",
        "Cocoa":        "CC=F"
    }
    data = {}
    for name, ticker in tickers.items():
        tk = yf.Ticker(ticker)
        info = tk.info
        price = info.get("regularMarketPrice") or info.get("previousClose") or None
        prev  = info.get("previousClose")
        pct = (price - prev) / prev * 100 if price is not None and prev else None
        data[name] = {"price": price, "change": pct}
    return data

commodity_data = load_commodity_data()

# ------------------------------------------------------------------------------
# 1. Persist selected country in session_state
# ------------------------------------------------------------------------------
if 'country' not in st.session_state:
    st.session_state['country'] = ''

# ------------------------------------------------------------------------------
# 2. Landing page: show flags until a country is chosen
# ------------------------------------------------------------------------------
if st.session_state['country'] == '':
    st.title("Select a Country")
    st.markdown("<div style='margin-bottom:40px'></div>", unsafe_allow_html=True)

    flags = [
        "Algeria", "Bahrain", "Egypt", "Jordan",
        "Kuwait",  "Lebanon", "Morocco", "Oman",
        "Qatar",   "Saudi",   "Tunisia","UAE"
    ]

    cols = st.columns(6)
    for idx, country in enumerate(flags[:6]):
        with cols[idx]:
            st.image(os.path.join("Flags", f"{country}.png"), use_container_width=True)
            if st.button(country, key=country):
                st.session_state['country'] = country
    st.markdown("<div style='margin-top:30px'></div>", unsafe_allow_html=True)

    cols = st.columns(6)
    for idx, country in enumerate(flags[6:]):
        with cols[idx]:
            st.image(os.path.join("Flags", f"{country}.png"), use_container_width=True)
            if st.button(country, key=country):
                st.session_state['country'] = country

    st.stop()

# ------------------------------------------------------------------------------
# 3. Non-Egypt warning + “Choose another country” button
# ------------------------------------------------------------------------------
if st.session_state['country'] != "Egypt":
    st.info("Forecasting is only available for Egypt.")
    if st.button("Choose another country"):
        st.session_state['country'] = ''
    st.stop()

# ------------------------------------------------------------------------------
# 4. Load Egyptian historical data
# ------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_data():
    df = pd.read_excel('Python Data New - Interface.xlsx')
    df['Year'] = pd.to_datetime(df['Year'])
    return (
        df.sort_values('Year')
          .dropna(subset=[
              'Global Inflation',
              'Egypt Inflation Lag2',
              'Global Inflation Lag2'
          ])
    )

df_hist = load_data()

# ------------------------------------------------------------------------------
# 5. Historical Data Explorer for Egypt
# ------------------------------------------------------------------------------
st.title("Historical Explorer — Egypt")
df_plot = (
    df_hist
    .set_index('Year')[['Global Inflation Lag2', 'Egypt Inflation Lag2']]
    .rename(columns={
        'Global Inflation Lag2': 'Global Inflation',
        'Egypt Inflation Lag2':  'Egypt Inflation'
    })
)

# ------------------------------------------------------------------------------
# 6. ECharts timeline with initial full-series display
# ------------------------------------------------------------------------------
frames = df_plot.index.strftime('%b %Y').tolist()
options = []
for i, frame in enumerate(frames):
    subset = df_plot.iloc[:i+1]
    options.append({
        'title': {'text': frame},
        'series': [
            {'data': subset['Global Inflation'].tolist()},
            {'data': subset['Egypt Inflation'].tolist()}
        ]
    })

chart_opts = {
    'baseOption': {
        'timeline': {
            'data': frames,
            'axisType': 'category',
            'autoPlay': False,
            'playInterval': 900,
            'currentIndex': len(frames) - 1
        },
        'tooltip': {'trigger': 'axis'},
        'legend': {
            'data': ['Global Inflation', 'Egypt Inflation'],
            'left': 'center'
        },
        'xAxis': {
            'type': 'category',
            'data': frames
        },
        'yAxis': {
            'type': 'value',
            'name': 'Inflation Rate (%)'
        },
        'series': [
            {'name': 'Global Inflation', 'type': 'line', 'smooth': True},
            {'name': 'Egypt Inflation',  'type': 'line', 'smooth': True}
        ]
    },
    'options': options
}

st_echarts(chart_opts, height="600px")

# ------------------------------------------------------------------------------
# 7. Live Food Commodity Ticker Tape (below the chart)
# ------------------------------------------------------------------------------
st.markdown("<h3 style='text-align:center; margin-top:2rem;'>Live Food Commodity Prices</h3>", unsafe_allow_html=True)

items = []
for name, stats in commodity_data.items():
    price = stats['price']
    pct   = stats['change']
    price_str = f"{price:.2f}$" if price is not None else "N/A"
    if pct is None:
        change_html = ""
    else:
        color = 'green' if pct >= 0 else 'red'
        sign  = '+' if pct >= 0 else ''
        change_html = f" <span style='color:{color};'>{sign}{pct:.2f}%</span>"
    items.append(f"<div class='ticker__item'>{name}: {price_str}{change_html}</div>")

html = f"""
<div class='ticker-wrap'>
  <div class='ticker'>
    {''.join(items)}
  </div>
</div>
"""
st.markdown(html, unsafe_allow_html=True)
