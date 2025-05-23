# pages/Nowcasting Food Bill.py

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import ElasticNet
import altair as alt

# ------------------------------------------------------------------------------
# Country check (must be Egypt)
# ------------------------------------------------------------------------------
if 'country' not in st.session_state or st.session_state['country'] != "Egypt":
    st.info("Forecasting is only available for Egypt.")
    st.stop()

# ------------------------------------------------------------------------------
# 1. Load & train the model
# ------------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_and_train():
    df = pd.read_excel('Python Data New - Interface.xlsx')
    df['Year'] = pd.to_datetime(df['Year'], dayfirst=True)
    df = (
        df.sort_values('Year')
          .dropna(subset=[
              'Exchange Rate Growth', 'Global Inflation',
              'Egypt Inflation Lag1', 'Egypt Inflation Lag2',
              'Global Inflation Lag1', 'Global Inflation Lag2',
              'Egypt Inflation'
          ])
    )
    features = [
        'Exchange Rate Growth', 'Global Inflation',
        'Egypt Inflation Lag1', 'Egypt Inflation Lag2',
        'Global Inflation Lag1', 'Global Inflation Lag2'
    ]
    model = ElasticNet(alpha=1.0, l1_ratio=0.9,
                       random_state=42, max_iter=10000)
    model.fit(df[features], df['Egypt Inflation'])
    return model, df

model, df_hist = load_and_train()

# ------------------------------------------------------------------------------
# 2. Page title
# ------------------------------------------------------------------------------
st.title(f"Nowcasting Food Bill — {st.session_state['country']}")

# ------------------------------------------------------------------------------
# 3. Sidebar: configuration & inputs
# ------------------------------------------------------------------------------
st.sidebar.header("Forecast Configuration")
n_periods = st.sidebar.number_input(
    "Months to forecast", min_value=1, max_value=60, value=1, step=1
)

last = df_hist.iloc[-1]
start_date = last['Year'] + pd.DateOffset(months=1)
forecast_dates = [start_date + pd.DateOffset(months=i) for i in range(n_periods)]

st.sidebar.subheader("Exchange Rate Growth")
exrg_future = [
    st.sidebar.number_input(
        f"ER Growth for {dt:%b %Y}", value=0.0,
        key=f"er_{dt.month}_{dt.year}"
    )
    for dt in forecast_dates
]

st.sidebar.subheader("Global Inflation")
gi_future = [
    st.sidebar.number_input(
        f"Global Inflation for {dt:%b %Y}", value=0.0,
        key=f"gi_{dt.month}_{dt.year}"
    )
    for dt in forecast_dates
]

if 'run_forecast' not in st.session_state:
    st.session_state['run_forecast'] = False
if st.sidebar.button("Run Forecast"):
    st.session_state['run_forecast'] = True
if not st.session_state['run_forecast']:
    st.info("Fill inputs on the left and click **Run Forecast**.")
    st.stop()

# ------------------------------------------------------------------------------
# 4. Perform forecasting loop
# ------------------------------------------------------------------------------
ei_lag1 = last['Egypt Inflation']
ei_lag2 = last['Egypt Inflation Lag1']
gi_lag1 = last['Global Inflation']
gi_lag2 = last['Global Inflation Lag1']

forecasts = []
for i, dt in enumerate(forecast_dates):
    feat = {
        'Exchange Rate Growth': exrg_future[i],
        'Global Inflation':     gi_future[i],
        'Egypt Inflation Lag1': ei_lag1,
        'Egypt Inflation Lag2': ei_lag2,
        'Global Inflation Lag1':gi_lag1,
        'Global Inflation Lag2':gi_lag2
    }
    pred = model.predict(pd.DataFrame([feat]))[0]
    forecasts.append({'Year': dt, 'Inflation': pred})
    ei_lag2, ei_lag1 = ei_lag1, pred
    gi_lag2, gi_lag1 = gi_lag1, gi_future[i]

df_fc = pd.DataFrame(forecasts)

# ------------------------------------------------------------------------------
# 5. Combined Line Chart: 2024 history + forecast (connected)
# ------------------------------------------------------------------------------
st.subheader("Egypt Inflation: 2024 Historical & Forecast")

# Historical 2024
hist_df = (
    df_hist[['Year', 'Egypt Inflation']]
      .rename(columns={'Egypt Inflation': 'Inflation'})
)
hist_df = hist_df[hist_df['Year'].dt.year == 2024]

# Build forecast‐plot df including the last historical point
fc_plot_df = pd.concat([
    pd.DataFrame([{
        'Year': last['Year'],
        'Inflation': last['Egypt Inflation']
    }]),
    df_fc
], ignore_index=True)

# Add Type labels
hist_df['Type'] = 'Historical'
fc_plot_df['Type'] = 'Forecast'

# Combine for unified legend
plot_df = pd.concat([hist_df, fc_plot_df], ignore_index=True)

# Base chart with legend inside at top-right
base = alt.Chart(plot_df).encode(
    x=alt.X('yearmonth(Year):T',
            axis=alt.Axis(title='', format='%b %Y', labelAngle=0)),
    y=alt.Y('Inflation:Q',
            axis=alt.Axis(title='Inflation Rate (%)')),
    color=alt.Color('Type:N',
                    scale=alt.Scale(domain=['Historical','Forecast'],
                                    range=['steelblue','orange']),
                    legend=alt.Legend(
                        title="",
                        orient="top-right",
                        direction="horizontal",
                        offset=35
                    )),
    strokeDash=alt.StrokeDash('Type:N',
                              scale=alt.Scale(domain=['Historical','Forecast'],
                                              range=[[],[4,4]]),
                              legend=None),
    detail=alt.Detail('Type:N')  # ensures continuous path
)
line = base.mark_line(interpolate='linear', strokeWidth=3)
points = (
    alt.Chart(plot_df[plot_df['Type']=='Forecast'])
      .mark_point(size=60)
      .encode(
          x='yearmonth(Year):T',
          y='Inflation:Q',
          color=alt.Color('Type:N',
                          scale=alt.Scale(domain=['Historical','Forecast'],
                                          range=['steelblue','orange']),
                          legend=None),
          tooltip=[
            alt.Tooltip('yearmonth(Year):T', title='Month', format='%b %Y'),
            alt.Tooltip('Inflation:Q', title='Inflation')
          ]
      )
)
chart = (line + points).properties(width=600, height=350)

# ------------------------------------------------------------------------------
# 6. Layout: center chart with shorter, vertically centered insights
# ------------------------------------------------------------------------------
col1, col2, col3 = st.columns([0.5, 3, 0.5])
with col1:
    st.markdown(
        """
        <div style="
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 350px;
        ">
            <div style="text-align: center;">
                <div style="font-size:18px; color:#444;">Total Imports-2024</div>
                <div style="font-size:24px; font-weight:bold;">7 Billion $</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    st.altair_chart(chart, use_container_width=True)
with col3:
    st.markdown(
        """
        <div style="
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 350px;
        ">
            <div style="text-align: center;">
                <div style="font-size:18px; color:#444;">Expected Imports</div>
                <div style="font-size:24px; font-weight:bold;">5 Billion $</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ------------------------------------------------------------------------------
# 7. Forecast Results Table (inside expander)
# ------------------------------------------------------------------------------
with st.expander("Show Forecast Data"):
    st.subheader("Forecast Results")
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']]
    st.table(table_df)
    st.download_button(
        "Download CSV", table_df.to_csv().encode(),
        file_name="inflation_forecasts.csv"
    )

# ------------------------------------------------------------------------------
# 8. Percentage Contributions
# ------------------------------------------------------------------------------
st.subheader("Percentage Contributions")
contrib_df = pd.DataFrame({
    'Category': ['World Food', 'Subsidy', 'Own Shocks'],
    'Value':    [8.7, 2.5, 76]
})
contrib_df['Dummy'] = ' '

contrib_chart = (
    alt.Chart(contrib_df)
      .mark_bar()
      .encode(
          y=alt.Y('Dummy:N', axis=None),
          x=alt.X('Value:Q', stack='zero', axis=alt.Axis(title='')),
          color=alt.Color('Category:N',
                          legend=alt.Legend(
                              title="",
                              orient='bottom',
                              direction='horizontal'
                          )),
          tooltip=['Category', 'Value']
      )
      .properties(width=600, height=200)
)
st.altair_chart(contrib_chart, use_container_width=True)
