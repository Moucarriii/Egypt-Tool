import streamlit as st
import pandas as pd
import os
from streamlit_echarts import st_echarts

# ------------------------------------------------------------------------------
# 0. Full-width layout + CSS tweaks
# ------------------------------------------------------------------------------
st.set_page_config(layout="wide")
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
</style>
""", unsafe_allow_html=True)

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

    # First row of 6 flags
    cols = st.columns(6)
    for idx, country in enumerate(flags[:6]):
        with cols[idx]:
            st.image(os.path.join("Flags", f"{country}.png"), use_container_width=True)
            if st.button(country, key=country):
                st.session_state['country'] = country

    st.markdown("<div style='margin-top:30px'></div>", unsafe_allow_html=True)

    # Second row of 6 flags
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
