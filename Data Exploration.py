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
# App-level password gate 
# ------------------------------------------------------------------------------ 
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def authenticate():
    st.session_state['authenticated'] = (st.session_state.get("pwd") == "ffd")

if not st.session_state['authenticated']:
    st.text_input("Enter password", type="password", key="pwd", on_change=authenticate)
    if st.session_state.get("pwd") and not st.session_state['authenticated']:
        st.error("Wrong password")
    st.stop()

# ------------------------------------------------------------------------------ 
# CSS tweaks 
# ------------------------------------------------------------------------------ 
st.markdown("""
<style>
.stImage > div { box-shadow: none !important; }

.stButton button {
    white-space: nowrap !important;
    background-color: #ffccbc !important;    /* light cyan */
    border: none !important;
    border-radius: 5px !important;
    padding: 0.5rem 1rem !important;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important;
    color: #000 !important;               /* dark teal text */
    width: 100% !important;
    margin: 0 !important;
}
.stButton button:focus,
.stButton button:hover {
    background-color: #ffab91 !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------ 
# Load live commodity prices + change percent 
# ------------------------------------------------------------------------------ 
@st.cache_data(show_spinner=False)
def load_commodity_data():
    tickers = {
        "Rice":"ZR=F","Wheat":"ZW=F","Maize":"ZC=F",
        "Soybeans":"ZS=F","Soybean Oil":"ZL=F","Soybean Meal":"ZM=F",
        "Sugar":"SB=F","Beef":"LE=F","Oranges":"OJ=F",
        "Coffee":"KC=F","Cocoa":"CC=F"
    }
    data = {}
    for name, symbol in tickers.items():
        try:
            info = yf.Ticker(symbol).info
            price = info.get("regularMarketPrice") or info.get("previousClose")
            prev  = info.get("previousClose")
            pct   = (price - prev)/prev*100 if price and prev else None
            data[name] = {"price": price, "change": pct}
        except Exception as e:
            st.warning(f"Failed to fetch data for {name}: {e}")
            data[name] = {"price": None, "change": None}  # Set to None if failure
    return data

commodity_data = load_commodity_data()

# ------------------------------------------------------------------------------ 
# Persist selected country 
# ------------------------------------------------------------------------------ 
if 'country' not in st.session_state:
    st.session_state['country'] = ''

# ------------------------------------------------------------------------------ 
# Landing page: flags 
# ------------------------------------------------------------------------------ 
if st.session_state['country'] == '':
    st.title("Select a Country")
    st.markdown("<div style='margin-bottom:40px'></div>", unsafe_allow_html=True)
    flags = ["Algeria","Bahrain","Egypt","Jordan","Kuwait","Lebanon",
             "Morocco","Oman","Qatar","Saudi","Tunisia","UAE"]
    cols = st.columns(6)
    for i, c in enumerate(flags[:6]):
        with cols[i]:
            st.image(os.path.join("Flags", f"{c}.png"), use_container_width=True)
            if st.button(c, key=c):
                st.session_state['country'] = c
    st.markdown("<div style='margin-top:30px'></div>", unsafe_allow_html=True)
    cols = st.columns(6)
    for i, c in enumerate(flags[6:]):
        with cols[i]:
            st.image(os.path.join("Flags", f"{c}.png"), use_container_width=True)
            if st.button(c, key=c):
                st.session_state['country'] = c
    st.stop()

if st.session_state['country'] != "Egypt":
    st.info("Forecasting is only available for Egypt.")
    if st.button("Choose another country"):
        st.session_state['country'] = ''
    st.stop()

# ------------------------------------------------------------------------------ 
# Load inflation data 
# ------------------------------------------------------------------------------ 
@st.cache_resource(show_spinner=False)
def load_inflation():
    df = pd.read_excel('Python Data New - Interface - Visuals.xlsx')
    df['Year'] = pd.to_datetime(df['Year'])
    return (
        df.sort_values('Year')
          .dropna(subset=['Global Inflation','Egypt Inflation'])
          .set_index('Year')[['Global Inflation','Egypt Inflation']]
          .round(2)
    )
df_infl = load_inflation()

# ------------------------------------------------------------------------------ 
# Load subsidies, imports, and NIR data 
# ------------------------------------------------------------------------------ 
@st.cache_resource(show_spinner=False)
def load_sub_imp_nir():
    df = pd.read_excel('Plots - Subsidies - Imports - NIR.xlsx')
    df['Year'] = pd.to_datetime(df['Year'], format='%Y')
    return (
        df.sort_values('Year')
          .dropna(subset=['Subsidies','Food Imports','NIR'])
          .set_index('Year')[['Subsidies','Food Imports','NIR']]
          .round(2)
    )
df_sub_imp_nir = load_sub_imp_nir()

# ------------------------------------------------------------------------------ 
# Explorer title + selector buttons 
# ------------------------------------------------------------------------------ 
st.title("Historical Explorer — Egypt")
if 'chart_choice' not in st.session_state:
    st.session_state['chart_choice'] = 'Inflation'

# wrap just these two in chart-btns so they shrink
st.markdown("<div class='chart-btns'>", unsafe_allow_html=True)
col1, col2, _ = st.columns([1,3,8])
with col1:
    if st.button("Inflation", key="btn_inf"):
        st.session_state['chart_choice'] = 'Inflation'
with col2:
    if st.button("Subsidies & Imports & NIR", key="btn_sub"):
        st.session_state['chart_choice'] = 'Subsidies & Imports & NIR'
st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------ 
# Prepare chart data 
# ------------------------------------------------------------------------------ 
if st.session_state['chart_choice'] == 'Inflation':
    df_plot = df_infl
    x_labels = df_plot.index.strftime('%b %Y').tolist()
else:
    df_plot = df_sub_imp_nir
    x_labels = df_plot.index.year.astype(str).tolist()

options = []
for i in range(len(x_labels)):
    slice_df = df_plot.iloc[:i+1]
    series = []
    for col in df_plot.columns:
        cfg = {'name': col, 'data': slice_df[col].tolist()}
        if st.session_state['chart_choice'] != 'Inflation' and col == 'NIR':
            cfg.update({'type': 'bar', 'yAxisIndex': 1})
        else:
            cfg.update({'type': 'line', 'smooth': True})
        series.append(cfg)
    options.append({'series': series})

# ------------------------------------------------------------------------------ 
# Axis settings (only left gridlines) 
# ------------------------------------------------------------------------------ 
if st.session_state['chart_choice'] == 'Inflation':
    y_axes = [ {
        'type': 'value',
        'name': 'Inflation (%)',
        'axisLabel': {'formatter': '{value}%'},
        'splitLine': {'show': True}
    } ]
else:
    y_axes = [ 
        {'type': 'value', 'name': 'Subsidies & Imports ($)', 'axisLabel': {'formatter': '${value}'}, 'splitLine': {'show': True}},
        {'type': 'value', 'name': 'NIR', 'position': 'right', 'axisLabel': {'formatter': '{value}'}, 'splitLine': {'show': False}}
    ]

# ------------------------------------------------------------------------------ 
# Optional annotations 
# ------------------------------------------------------------------------------ 
graphics = []
if st.session_state['chart_choice']=='Inflation' and st.checkbox("Show annotations", key="anno"):
    graphics = [
        {'type':'text','left':'35%','top':'20%','style':{'text':'Currency Devaluation','fill':'#91CC75','font':'14px sans-serif'}},
        {'type':'text','left':'12%','top':'20%','style':{'text':'Global supply, \noil prices eased','fill':'#5470C6','font':'14px sans-serif'}}
    ]

# ------------------------------------------------------------------------------ 
# Chart config & render 
# ------------------------------------------------------------------------------ 
chart_opts = {
    'baseOption': {
        'timeline': {
            'data': x_labels,
            'axisType': 'category',
            'autoPlay': False,
            'playInterval': 900,
            'currentIndex': len(x_labels)-1,
            'left': '5%', 'right': '5%',
            'label': {'show': False}, 'axisLabel': {'show': False}
        },
        'tooltip': {'trigger':'axis'},
        'legend': {'data': list(df_plot.columns), 'left': 'center'},
        'xAxis': {'type':'category','data': x_labels},
        'yAxis': y_axes,
        'series': options[-1]['series'],
        'graphic': graphics
    },
    'options': options
}
st_echarts(chart_opts, height="600px")

# ------------------------------------------------------------------------------ 
# Live Food Commodity Ticker Tape 
# ------------------------------------------------------------------------------ 
items = []
for name, s in commodity_data.items():
    price, chg = s['price'], s['change']
    pr_s = f"{price:.2f}$" if price else "N/A"
    ch_s = f"<span style='color:{'green' if chg>=0 else 'red'};'>{'+' if chg>=0 else ''}{chg:.2f}%</span>" if chg is not None else ""
    items.append(f"<div class='ticker__item'>{name}: {pr_s} {ch_s}</div>")
html = f"<div class='ticker-wrap'><div class='ticker'>{''.join(items)}</div></div>"
st.markdown(html, unsafe_allow_html=True)
