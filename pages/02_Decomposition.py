# 8. Percentage Contributions
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model  import Ridge
import time 

# --------------------------------------------------------------------------
# 8. Percentage Contributions with interactive year selection and stacked bar chart
# --------------------------------------------------------------------------
st.subheader("Percentage Contributions")

# Grab the forecast dataframe you computed earlier
if 'df_fc' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first.")
    st.stop()

df_fc = st.session_state['df_fc']

# Grab forecast_dates from session state
if 'forecast_dates' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first to generate the forecast.")
    st.stop()

forecast_dates = st.session_state['forecast_dates']

# Grab start_date from session state
if 'start_date' not in st.session_state:
    st.error("You need to run the Nowcasting Food Bill Page first to generate the forecast.")
    st.stop()

start_date = st.session_state['start_date']

# Now you can safely use forecast_dates in your code

# 7. Forecast Results Table
# --------------------------------------------------------------------------
with st.expander("Show Forecast Data"):
    st.subheader("Forecast Results")
    table_df = df_fc.set_index(df_fc['Year'].dt.strftime('%b %Y'))[['Inflation']]
    st.table(table_df)
    st.download_button("Download CSV", table_df.to_csv().encode(),
                       file_name="inflation_forecasts.csv")

# --------------------------------------------------------------------------

# Load the full dataset for contributions
xlsx_path = "StackedBar - Copy.xlsx"
contrib_full_df = pd.read_excel(xlsx_path)

# Year selection dropdown
selected_year = st.selectbox(
    "Select Year for Contribution Breakdown",
    options=contrib_full_df['Year'].astype(str).tolist()
)

# Filter dataset for selected year
row = contrib_full_df[contrib_full_df['Year'].astype(str) == selected_year].iloc[0]
year_label = str(int(row["Year"]))

# Define desired legend order
desired_order = [
    "World Food Price (increase)",
    "World Food Price (decrease)",
    "Exchange Rate (depreciation)",
    "Exchange Rate (appreciation)",
    "Other Factors",
    "Unexplained (residuals)"
]

# Extract values in that order
cats = []
vals = []
for cat in desired_order:
    if cat in row.index:
        cats.append(cat)
        vals.append(float(row[cat]))

# Split into negative and positive preserving order
neg_data = []
pos_data = []
for cat, val in zip(cats, vals):
    if val < 0:
        neg_data.append((cat, val))
    else:
        pos_data.append((cat, val))

# Define colors
color_map = {
    "World Food Price (increase)": "#1F3B73",
    "World Food Price (decrease)": "#8B0000",
    "Exchange Rate (depreciation)": "#89CFF0",
    "Exchange Rate (appreciation)": "#F08080",
    "Other Factors": "#FFB347",
    "Unexplained (residuals)": "#FF8C00"
}

# Build Plotly figure
fig = go.Figure()

neg_base = 0.0
for cat, val in neg_data:
    fig.add_trace(go.Bar(
        y=[year_label],
        x=[val],
        name=cat,
        orientation='h',
        marker=dict(color=color_map[cat]),
        base=[neg_base],
        customdata=[val],
        hovertemplate=f"<b>{cat}</b><br>Value: %{{customdata}}<extra></extra>"
    ))
    neg_base += val

pos_base = 0.0
for cat, val in pos_data:
    fig.add_trace(go.Bar(
        y=[year_label],
        x=[val],
        name=cat,
        orientation='h',
        marker=dict(color=color_map[cat]),
        base=[pos_base],
        customdata=[val],
        hovertemplate=f"<b>{cat}</b><br>Value: %{{customdata}}<extra></extra>"
    ))
    pos_base += val

fig.update_layout(
    title=dict(
        text="Decomposition of Domestic Food Price Change in Egypt",
        x=0.5, xanchor="center",
        font=dict(size=16)
    ),
    barmode='relative',
    template='plotly_white',
    height=350,
    margin=dict(l=40, r=40, t=60, b=80),
    xaxis=dict(
        title="",
        showline=True,
        linecolor="black",
        linewidth=1,
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="black",
        showgrid=False,
        tickmode='array',
        tickvals=[-100, -80, -60, -40, -20, 0, 20, 40, 60, 80, 100, 120, 140, 160],
        ticks="outside",
        tickfont=dict(size=12)
    ),
    yaxis=dict(
        title="",
        tickmode='array',
        tickvals=[year_label],
        ticktext=[year_label],
        ticks="",
        showgrid=False,
        showline=False
    ),
    legend=dict(
        orientation="h",
        y=-0.25,
        x=0.5,
        xanchor="center",
        yanchor="top",
        font=dict(size=12),
        bgcolor="rgba(0,0,0,0)"
    ),
    showlegend=True
)

st.plotly_chart(fig, use_container_width=True)
