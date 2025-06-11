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
n_periods = st.sidebar.number_input( 
    "Months to forecast", min_value=1, max_value=60, value=1, step=1 
)

last = df_hist.iloc[-1] 
start_date = last['Year'] + pd.DateOffset(months=1) 
forecast_dates = [start_date + pd.DateOffset(months=i) for i in range(n_periods)]

# Store forecast_dates in session state for use in other tabs
st.session_state['forecast_dates'] = forecast_dates
st.session_state['start_date'] = start_date

st.sidebar.subheader("Exchange Rate Growth") 
exrg_future = [ 
    st.sidebar.number_input( 
        f"Exchange Rate for {dt:%b %Y}", value=0.0, 
        key=f"er_{dt.month}_{dt.year}" 
    ) for dt in forecast_dates 
]

st.sidebar.subheader("Global Inflation") 
gi_future = [ 
    st.sidebar.number_input( 
        f"Global Inflation for {dt:%b %Y}", value=0.0, 
        key=f"gi_{dt.month}_{dt.year}" 
    ) for dt in forecast_dates 
]

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
        'Exchange Rate Growth': exrg_future[i], 
        'Global Inflation': gi_future[i], 
        'Egypt Inflation Lag1': ei_lag1, 
        'Egypt Inflation Lag2': ei_lag2, 
        'Global Inflation Lag1': gi_lag1 
    } 
    pred = model.predict(pd.DataFrame([feat]))[0] 
    forecasts.append({'Year': dt, 'Inflation': pred}) 
    ei_lag2, ei_lag1 = ei_lag1, pred 
    gi_lag1 = gi_future[i]

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
if view == 'Yearly average': 
    st.subheader("Yearly Average Inflation: Historical vs Forecast") 
    hist_avg = ( 
        df_hist.assign(Year=df_hist['Year'].dt.year) 
               .groupby('Year', as_index=False)['Egypt Inflation'] 
               .mean() 
               .rename(columns={'Egypt Inflation':'Inflation'}) 
    ) 
    hist_avg['Type'] = 'Historical' 
    fc_avg = ( 
        df_fc.assign(Year=df_fc['Year'].dt.year) 
             .groupby('Year', as_index=False)['Inflation'] 
             .mean() 
    ) 
    fc_avg['Type'] = 'Forecast' 
    plot_df = pd.concat([hist_avg, fc_avg], ignore_index=True) 

    yearly = alt.Chart(plot_df).mark_line(interpolate='linear', strokeWidth=3).encode( 
        x=alt.X('Year:O', axis=alt.Axis(title='Year', labelAngle=0)), 
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Avg Inflation (%)')), 
        color=alt.Color('Type:N', 
                        scale=alt.Scale(domain=['Historical','Forecast'], 
                                        range=['steelblue','orange']), 
                        legend=alt.Legend(title=None, orient='top-right')),  
        strokeDash=alt.StrokeDash('Type:N', 
                                  scale=alt.Scale(domain=['Historical','Forecast'], 
                                                  range=[[],[4,4]]), 
                                  legend=None) 
    ) 
    pts = alt.Chart(plot_df[plot_df['Type']=='Forecast']).mark_point(size=100).encode( 
        x='Year:O', 
        y='Inflation:Q', 
        color=alt.value('orange') 
    ) 
    st.altair_chart((yearly + pts).properties(width=700, height=400), 
                    use_container_width=True) 

else: 
    st.subheader("Monthly Inflation: Last Historical Year & Forecast") 
    last_year = df_hist['Year'].dt.year.max() 
    hist_monthly = ( 
        df_hist[df_hist['Year'].dt.year == last_year] 
               [['Year','Egypt Inflation']] 
               .rename(columns={'Egypt Inflation':'Inflation'}) 
    ) 
    hist_monthly['Type'] = 'Historical' 
    fc_monthly = df_fc.copy() 
    fc_monthly['Type'] = 'Forecast' 
    monthly_df = pd.concat([hist_monthly, fc_monthly], ignore_index=True) 

    base = alt.Chart(monthly_df).encode( 
        x=alt.X('yearmonth(Year):T', 
                axis=alt.Axis(title='', format='%b %Y', labelAngle=0)), 
        y=alt.Y('Inflation:Q', axis=alt.Axis(title='Inflation Rate (%)')), 
        color=alt.Color('Type:N', 
                        scale=alt.Scale(domain=['Historical','Forecast'], 
                                        range=['steelblue','orange']), 
                        legend=alt.Legend(title=None, orient='top-right')) 
    ) 
    line = base.mark_line(strokeWidth=3) 
    pts = base.mark_point(size=60).transform_filter(alt.datum.Type=='Forecast') 
    st.altair_chart((line + pts).properties(width=700, height=350), use_container_width=True)

# -------------------------------------------------------------------------- 
# 7. Forecast Results Table 
# -------------------------------------------------------------------------- 
with st.expander("Show Forecast Data"): 
    st.subheader("Forecast Results") 
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']] 
    st.table(table_df) 
    st.download_button("Download CSV", table_df.to_csv().encode(), 
                       file_name="inflation_forecasts.csv") 
