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
.stButton button { display: block; margin: 0 auto; }
.ticker-wrap {
    width: 60%; margin: 1rem auto; overflow: hidden;
    background: #f5f5f5; border-top:1px solid #ddd;
    border-bottom:1px solid #ddd; padding:0.5rem 0;
}
.ticker {
    display: inline-block; white-space: nowrap;
    padding-left: 100%; animation: scroll 40s linear infinite;
}
.ticker__item {
    display: inline-block; padding: 0 2rem;
    font-size:1.1rem; color:#333;
}
@keyframes scroll {
    0% { transform: translateX(0); }
    100% { transform: translateX(-100%); }
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
    for name, t in tickers.items():
        info = yf.Ticker(t).info
        price = info.get("regularMarketPrice") or info.get("previousClose")
        prev  = info.get("previousClose")
        pct   = (price - prev)/prev*100 if price and prev else None
        data[name] = {"price": price, "change": pct}
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
# Explorer title + selector
# ------------------------------------------------------------------------------
st.title("Historical Explorer — Egypt")
chart_choice = st.radio("Select chart:", ["Inflation","Subsidies & Imports & NIR"], horizontal=True)

# Choose DataFrame and x-axis labels
if chart_choice == "Inflation":
    df_plot = df_infl
    x_labels = df_plot.index.strftime('%b %Y').tolist()
else:
    df_plot = df_sub_imp_nir
    x_labels = df_plot.index.year.astype(str).tolist()

# Build timeline options with NIR as bar
options = []
for i, label in enumerate(x_labels):
    sub = df_plot.iloc[:i+1]
    series = []
    for col in df_plot.columns:
        s = {
            'name': col,
            'data': sub[col].tolist()
        }
        if col == 'NIR':
            s.update({'type': 'bar', 'yAxisIndex': 1})
        else:
            s.update({'type': 'line', 'smooth': True})
        series.append(s)
    options.append({
        'title': {'text': label},
        'series': series
    })

# Annotations only for inflation
graphics = []
if chart_choice == "Inflation" and st.checkbox("Show annotations", False):
    graphics = [
        {'type':'text','left':'35%','top':'21%',
         'style':{'text':'The Central Bank floated the pound,\ncausing a 50% devaluation\nand a sharp rise in prices',
                  'fill':'#91CC75','font':'14px sans-serif'}},
        {'type':'text','left':'10%','top':'21%',
         'style':{'text':'Global crop supply improved\nand oil prices eased, driving down food prices',
                  'fill':'#5470C6','font':'14px sans-serif'}}
    ]

# Chart configuration with dual y-axes
chart_opts = {
    'baseOption': {
        'timeline': {
            'data': x_labels,
            'axisType': 'category',
            'autoPlay': False,
            'playInterval': 900,
            'currentIndex': len(x_labels) - 1
        },
        'tooltip': {'trigger': 'axis'},
        'legend': {'data': list(df_plot.columns), 'left': 'center'},
        'xAxis': {'type': 'category', 'data': x_labels},
        'yAxis': [
            {
                'type': 'value',
                'name': chart_choice.replace('& NIR','') + ' ($)',
                'axisLabel': {'formatter': '${value}'}
            },
            {
                'type': 'value',
                'name': 'NIR',
                'position': 'right'
            }
        ],
        'series': series,
        'graphic': graphics
    },
    'options': options
}

st_echarts(chart_opts, height="600px")

# ------------------------------------------------------------------------------
# Live Food Commodity Ticker Tape
# ------------------------------------------------------------------------------
st.markdown("<h3 style='text-align:center; margin-top:2rem;'>Live Food Commodity Prices</h3>",
            unsafe_allow_html=True)
items = []
for name, s in commodity_data.items():
    price, chg = s['price'], s['change']
    pr_s = f"{price:.2f}$" if price else "N/A"
    ch_s = f"<span style='color:{'green' if chg>=0 else 'red'};'>{'+' if chg>=0 else ''}{chg:.2f}%</span>" if chg else ""
    items.append(f"<div class='ticker__item'>{name}: {pr_s} {ch_s}</div>")

html = f"<div class='ticker-wrap'><div class='ticker'>{''.join(items)}</div></div>"
st.markdown(html, unsafe_allow_html=True)
