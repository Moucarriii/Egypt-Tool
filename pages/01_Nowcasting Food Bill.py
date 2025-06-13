# pages/Nowcasting Food Bill.py

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model  import Ridge
import time 

# ------------------------------------------------------------------------------ 
# Button styling: colored backgrounds, shading, no-wrap 
# ------------------------------------------------------------------------------ 
st.markdown(""" 
<style> 
/* All selector buttons */ 
.stButton button { 
    white-space: nowrap !important; 
    background-color: #ffccbc !important;    /* light cyan */ 
    border-radius: 5px !important; 
    padding: 0.5rem 1rem !important; 
    box-shadow: 2px 2px 5px rgba(0,0,0,0.1) !important; 
    color: #000 !important;               /* dark teal text */ 
} 
/* Highlight active button */ 
.stButton button:focus, .stButton button:hover { 
    background-color: #ffab91 !important; 
} 
</style> 
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------- 
# Country check (must be Egypt) 
# -------------------------------------------------------------------------- 
if 'country' not in st.session_state or st.session_state['country'] != "Egypt": 
    st.info("Forecasting is only available for Egypt.") 
    st.stop() 

# -------------------------------------------------------------------------- 
# 1. Load & train the model 
# -------------------------------------------------------------------------- 
@st.cache_resource(show_spinner=False) 
def load_and_train(): 
    df = pd.read_excel('Python Data New - Interface -newJune11.xlsx') 
    df['Year'] = pd.to_datetime(df['Year'], dayfirst=True) 
    df = df.sort_values('Year').dropna(subset=[ 
        'Exchange Rate Growth','Global Inflation', 
        'Egypt Inflation Lag1','Egypt Inflation Lag2', 
        'Global Inflation Lag1','Global Inflation Lag2', 
        'Egypt Inflation' 
    ]) 
    features = [ 
        'Exchange Rate Growth','Global Inflation', 
        'Egypt Inflation Lag1','Egypt Inflation Lag2', 
        'Global Inflation Lag1' 
    ] 
    model = Pipeline([ 
        ('scaler', StandardScaler()), 
        ('ridge', Ridge(alpha=0.001, random_state=42)) 
    ]) 
    model.fit(df[features], df['Egypt Inflation']) 
    return model, df

model, df_hist = load_and_train()

# -------------------------------------------------------------------------- 
# 2. Page title 
# -------------------------------------------------------------------------- 
st.title("Nowcasting Food Bill — Egypt")

# -------------------------------------------------------------------------- 
# 3. Sidebar: configuration & inputs 
# -------------------------------------------------------------------------- 
st.sidebar.header("Forecast Configuration") 

# Only one fixed value: 12 months forecast 
n_periods = 12  # Fixed to 12 months

# Set the start date to be 1 month after the last historical entry
last = df_hist.iloc[-1] 
start_date = last['Year'] + pd.DateOffset(months=1) 
forecast_dates = [start_date + pd.DateOffset(months=i) for i in range(n_periods)]

# Store forecast_dates in session state for use in other tabs
st.session_state['forecast_dates'] = forecast_dates
st.session_state['start_date'] = start_date

# User inputs for Exchange Rate Growth and Global Inflation (for the full 12 months)
st.sidebar.subheader("Exchange Rate Growth") 
exrg_input = st.sidebar.number_input("Enter Exchange Rate Growth (%) for 12 months", value=0.0)

st.sidebar.subheader("Global Inflation") 
gi_input = st.sidebar.number_input("Enter Global Inflation (%) for 12 months", value=0.0)

# "Run Forecast" button to trigger forecast computation
if 'run_forecast' not in st.session_state: 
    st.session_state['run_forecast'] = False 
if st.sidebar.button("Run Forecast"): 
    st.session_state['run_forecast'] = True 

if not st.session_state['run_forecast']: 
    st.info("Fill inputs on the left and click **Run Forecast**.") 
    st.stop()

# -------------------------------------------------------------------------- 
# 4. Perform forecasting loop 
# -------------------------------------------------------------------------- 
ei_lag1 = last['Egypt Inflation'] 
ei_lag2 = last['Egypt Inflation Lag1'] 
gi_lag1 = last['Global Inflation'] 

forecasts = [] 
for i, dt in enumerate(forecast_dates): 
    feat = { 
        'Exchange Rate Growth': exrg_input,  # Now a fixed value for the 12 months
        'Global Inflation': gi_input,  # Now a fixed value for the 12 months
        'Egypt Inflation Lag1': ei_lag1, 
        'Egypt Inflation Lag2': ei_lag2, 
        'Global Inflation Lag1': gi_lag1 
    } 
    pred = model.predict(pd.DataFrame([feat]))[0] 
    forecasts.append({'Year': dt, 'Inflation': pred}) 
    ei_lag2, ei_lag1 = ei_lag1, pred 
    gi_lag1 = gi_input  # Update lag with the same input value

df_fc = pd.DataFrame(forecasts)

# Store df_fc in session_state for later use in other pages
st.session_state['df_fc'] = df_fc

# -------------------------------------------------------------------------- 
# 5. View selector: two buttons in columns [1,3,8] 
# -------------------------------------------------------------------------- 
if 'view_choice' not in st.session_state: 
    st.session_state['view_choice'] = 'Yearly average' 

col1, col2, _ = st.columns([1, 1, 8]) 
with col1: 
    if st.button("Yearly average", key="btn_yearly"): 
        st.session_state['view_choice'] = 'Yearly average' 
with col2: 
    if st.button("Monthly detail", key="btn_monthly"): 
        st.session_state['view_choice'] = 'Monthly detail'

view = st.session_state['view_choice']

# -------------------------------------------------------------------------- 
# 6. Charts based on selection 
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# 6. Charts based on selection (UPDATED)
# --------------------------------------------------------------------------
if view == 'Yearly average':
    st.subheader("Yearly Average Inflation: Historical vs Forecast")

    # Historical averages
    hist_avg = (
        df_hist.assign(Year=df_hist['Year'].dt.year)
               .groupby('Year', as_index=False)['Egypt Inflation']
               .mean()
               .rename(columns={'Egypt Inflation':'Inflation'})
    )
    hist_avg['Type'] = 'Historical'

    # Forecast averages
    fc_avg = (
        df_fc.assign(Year=df_fc['Year'].dt.year)
             .groupby('Year', as_index=False)['Inflation']
             .mean()
    )
    fc_avg['Type'] = 'Forecast'

    # Build a two-point segment so the forecast line connects to the last historical point
    last_hist = hist_avg[hist_avg['Year'] == hist_avg['Year'].max()][['Year','Inflation']]
    fc_segment = pd.concat([last_hist, fc_avg], ignore_index=True)

    # Plot historical line
    hist_line = alt.Chart(hist_avg).mark_line(strokeWidth=3).encode(
        x=alt.X('Year:O', axis=alt.Axis(title='Year', labelAngle=0)),
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Avg Inflation (%)')),
        color=alt.value('steelblue')
    )

    # Plot forecast segment (dashed)
    fc_line = alt.Chart(fc_segment).mark_line(strokeWidth=3, strokeDash=[4,4]).encode(
        x='Year:O',
        y='Inflation:Q',
        color=alt.value('orange')
    )

    # Plot forecast points
    fc_pts = alt.Chart(fc_avg).mark_point(size=100).encode(
        x='Year:O',
        y='Inflation:Q',
        color=alt.value('orange')
    )

    # Combine and render
    st.altair_chart((hist_line + fc_line + fc_pts)
                    .properties(width=700, height=400),
                    use_container_width=True)

else:
    st.subheader("Monthly Inflation: Last Historical Year & Forecast")

    # Historical monthly for the last year
    last_year = df_hist['Year'].dt.year.max()
    hist_monthly = (
        df_hist[df_hist['Year'].dt.year == last_year]
               [['Year','Egypt Inflation']]
               .rename(columns={'Egypt Inflation':'Inflation'})
    )
    hist_monthly['Type'] = 'Historical'

    # Forecast monthly
    fc_monthly = df_fc.copy()
    fc_monthly['Type'] = 'Forecast'

    # Build a two-point segment so the forecast line connects to the last historical month
    last_month = hist_monthly.iloc[[-1]][['Year','Inflation']]
    fc_segment_monthly = pd.concat(
        [last_month, fc_monthly[['Year','Inflation']]],
        ignore_index=True
    )

    # Plot historical line
    hist_line_m = alt.Chart(hist_monthly).mark_line(strokeWidth=3).encode(
        x=alt.X('yearmonth(Year):T', axis=alt.Axis(title='', format='%b %Y', labelAngle=0)),
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Inflation Rate (%)')),
        color=alt.value('steelblue')
    )

    # Plot forecast segment (dashed)
    fc_line_m = alt.Chart(fc_segment_monthly).mark_line(strokeWidth=3, strokeDash=[4,4]).encode(
        x=alt.X('yearmonth(Year):T'),
        y='Inflation:Q',
        color=alt.value('orange')
    )

    # Plot forecast points
    fc_pts_m = alt.Chart(fc_monthly).mark_point(size=60).encode(
        x=alt.X('yearmonth(Year):T'),
        y='Inflation:Q',
        color=alt.value('orange')
    )

    # Combine and render
    st.altair_chart((hist_line_m + fc_line_m + fc_pts_m)
                    .properties(width=700, height=350),
                    use_container_width=True)

# -------------------------------------------------------------------------- 
# 7. Forecast Results Table 
# -------------------------------------------------------------------------- 
with st.expander("Show Forecast Data"): 
    st.subheader("Forecast Results") 
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']] 
    st.table(table_df) 
    st.download_button("Download CSV", table_df.to_csv().encode(), 
                       file_name="inflation_forecasts.csv") 
